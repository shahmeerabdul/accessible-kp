// Ask the browser for the visitor's position. Only ever called from a button
// click: the browser then shows its own permission prompt.
//
// Coordinates are rounded to 3 decimals (about 110 m). That is plenty to find
// nearby facilities and avoids sending a more precise location than needed.
// Note: browsers only allow geolocation on HTTPS pages (and on localhost).

export function describeGeolocationError(error) {
  switch (error?.code) {
    case 1:
      return "Location permission was denied. You can still choose a city.";
    case 2:
      return "Your location is not available right now. You can still choose a city.";
    case 3:
      return "Finding your location took too long. Please try again.";
    default:
      return "We could not get your location. You can still choose a city.";
  }
}

export function getCurrentCoordinates() {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject({ code: 0, message: "unsupported" });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          lat: Math.round(position.coords.latitude * 1000) / 1000,
          lon: Math.round(position.coords.longitude * 1000) / 1000,
        }),
      (error) => reject(error),
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 300000 }
    );
  });
}
