# Deploying to AWS (S3 + CloudFront for the frontend, EC2 for the API)

```
Browser ──HTTPS──> CloudFront ──> S3 bucket        (static React build)
   │
   └──HTTPS──> api.example.com ──> nginx ──> gunicorn (Django)   on one EC2 instance
                                                │
                                                └──> healthsites.io / Overpass
                                          (optional: ElastiCache Redis for the cache)
```

Use your own domain names wherever you see `example.com`. Nothing here has been run against
a real AWS account, so treat it as a checklist to adapt, not a script to paste blindly.

## 1. The API on EC2

**Instance:** a small one is enough (for example `t3.micro` or `t4g.small`). The app has no
database and the work is waiting on an upstream API.

**Security group:** allow 80 and 443 from anywhere. Allow 22 only from your IP, or skip SSH
and use SSM Session Manager. Do **not** open port 8000: gunicorn must only be reachable
through nginx (see "Why this matters" below).

**Install** (Amazon Linux 2023; any Python 3.10+ works, adjust the package names to your OS):

```bash
sudo dnf install -y python3.12 nginx git
sudo useradd --system --create-home accessible-kpk
sudo git clone https://github.com/shahmeerabdul/accessible-kp.git /opt/accessible-kp
cd /opt/accessible-kp/backend
sudo python3.12 -m venv .venv
sudo .venv/bin/pip install -r requirements-prod.txt
sudo chown -R accessible-kpk: /opt/accessible-kp
```

**Settings:** create `/etc/accessible-kpk.env`, owned by root with mode `600`:

```env
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<a long random value: python -c "import secrets; print(secrets.token_urlsafe(64))">
DJANGO_ALLOWED_HOSTS=api.example.com
CORS_ALLOWED_ORIGINS=https://app.example.com
FACILITIES_PROVIDER=healthsites
HEALTHSITES_API_KEY=<your key>
API_NUM_PROXIES=1
# Optional: share the cache between workers/servers
# REDIS_URL=rediss://<your-elasticache-endpoint>:6379/0
```

The app refuses to start in production mode if the secret key, allowed hosts or CORS origins
are missing or still placeholders, so a mistake fails loudly.

**Keep the healthsites key out of the repo and AMI.** Instead of typing it into the file by
hand you can store it in SSM Parameter Store (as a `SecureString`), give the instance an IAM
role that can read just that parameter, and write the env file at boot:

```bash
aws ssm get-parameter --name /accessible-kpk/healthsites-api-key --with-decryption \
  --query Parameter.Value --output text
```

**Run it:** copy [accessible-kpk.service](accessible-kpk.service) to
`/etc/systemd/system/` and [nginx.conf.example](nginx.conf.example) to
`/etc/nginx/conf.d/accessible-kpk.conf`, edit the domain, then:

```bash
sudo certbot --nginx -d api.example.com     # TLS certificate (or terminate TLS on an ALB with ACM)
sudo systemctl daemon-reload
sudo systemctl enable --now accessible-kpk
sudo systemctl enable --now nginx
curl https://api.example.com/api/health      # {"status": "ok"}
```

**Behind an ALB instead of certbot:** terminate TLS on the load balancer, point the target
group's health check at `/api/health`, and set `API_NUM_PROXIES=2` (ALB + nginx) so rate
limiting sees real client IPs. The health path is exempt from Django's HTTPS redirect so a
plain-HTTP check works.

### Settings that matter in production

| Variable | Meaning |
|---|---|
| `DJANGO_DEBUG` | Must be `false`. |
| `DJANGO_SECRET_KEY` | Unique and secret. |
| `DJANGO_ALLOWED_HOSTS` | Your API host name(s), never `*`. |
| `CORS_ALLOWED_ORIGINS` | The frontend origin(s), e.g. your CloudFront URL. |
| `DJANGO_SECURE_SSL_REDIRECT` | Redirect HTTP to HTTPS (default `true`). |
| `DJANGO_BEHIND_PROXY` | Trust `X-Forwarded-Proto` from nginx/ALB (default `true`). |
| `DJANGO_HSTS_SECONDS` | HSTS lifetime, default `3600`. Raise to `31536000` once HTTPS works everywhere. |
| `API_NUM_PROXIES` | Number of proxies in front of Django. |
| `REDIS_URL` | Shared cache; unset means per-process memory. |
| `LOG_LEVEL` | `INFO` by default. |

Run `python manage.py check --deploy` (with those variables set) to have Django audit the
configuration.

### Why this matters

With `DJANGO_BEHIND_PROXY=true`, Django believes the `X-Forwarded-Proto` header. That is only
safe if every request really comes through nginx/ALB, which overwrites that header. If
gunicorn were reachable directly, a client could send a fake header. That is why the service
file binds gunicorn to `127.0.0.1` and the security group never opens port 8000.

### Visitor location privacy

The "Use my location" feature sends the visitor's coordinates to the API as `?lat=…&lon=…`.
The app does not store them, but web-server access logs normally record the full URL. Both
shipped configs avoid that: gunicorn logs the path only (`gunicorn.conf.py`) and the nginx
example uses a `$uri`-based `log_format`. Keep this if you change the logging, and be aware
that CloudFront, an ALB or other layers in front of the API have their own access logs that
can include query strings.

If the cache (Redis) is unreachable the API keeps working: it skips the cache and the rate
limiter allows requests, and logs a warning. It just calls the upstream API more often.

## 2. The frontend on S3 + CloudFront

The frontend is a static site. The API address is **baked in at build time**, so build it
with your real API URL:

```bash
cd frontend
npm ci
VITE_API_BASE_URL=https://api.example.com npm run build
aws s3 sync dist s3://your-frontend-bucket --delete
```

- Keep the bucket **private** and serve it through CloudFront with an Origin Access Control
  (a plain S3 website endpoint is HTTP-only, which breaks calling an HTTPS API).
- Set the default root object to `index.html`.
- Add custom error responses so deep links work: `403` and `404` → `/index.html` with status `200`.
- After each deploy, invalidate the cache: `aws cloudfront create-invalidation --distribution-id <id> --paths "/*"`.
- Put the CloudFront (or custom) domain in the API's `CORS_ALLOWED_ORIGINS`.

## 3. Map tiles

The map uses OpenStreetMap's public tile servers, which are fine for development and light
use but not for heavy traffic (see their tile usage policy). Before a public launch, switch
`MapView.jsx` to a keyed tile provider.

## Docker alternative

`docker compose up --build` from the repository root runs the API, the frontend and Redis
locally (see the main README). The same two images can be run on EC2, ECS or App Runner, but
note the images do not include TLS: put an ALB or nginx in front.
