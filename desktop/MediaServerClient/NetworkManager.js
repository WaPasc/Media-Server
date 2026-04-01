.pragma library

const BASE_URL = "http://127.0.0.1:8000";

// The core request engine using Promises
function request(method, endpoint, body = null) {
    return new Promise(function (resolve, reject) {
        var xhr = new XMLHttpRequest();
        xhr.open(method, BASE_URL + endpoint);

        // TODO: When we build User Auth later, we will inject the JWT token here
        // xhr.setRequestHeader("Authorization", "Bearer " + token);

        if (body !== null) {
            xhr.setRequestHeader("Content-Type", "application/json");
        }

        // Triggered when the server responds
        xhr.onload = function () {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    if (xhr.responseText) {
                        let jsonResponse = JSON.parse(xhr.responseText);
                        resolve(jsonResponse);
                    } else {
                        resolve({}); // Empty response (like 204 Delete), just resolve safely
                    }
                } catch (err) {
                    reject("JSON Parse Error: " + err);
                }
            } else {
                reject("API Error: " + xhr.status + " " + xhr.statusText);
            }
        };

        // Triggered if the network drops or the backend is turned off
        xhr.onerror = function () {
            reject("Network request failed. Is the FastAPI backend running?");
        };

        // Execute the request
        xhr.send(body ? JSON.stringify(body) : null);
    });
}

function get(endpoint) {
    return request("GET", endpoint);
}

function post(endpoint, body) {
    return request("POST", endpoint, body);
}

function del(endpoint) {
    return request("DELETE", endpoint);
}
