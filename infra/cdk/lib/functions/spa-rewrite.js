function handler(event) {
  var request = event.request;
  var uri = request.uri;

  if (request.method !== "GET" && request.method !== "HEAD") {
    return request;
  }

  if (
    uri === "/api" ||
    uri.indexOf("/api/") === 0 ||
    uri.indexOf("/assets/") === 0 ||
    /\.[^/]+$/.test(uri)
  ) {
    return request;
  }

  request.uri = "/index.html";
  return request;
}
