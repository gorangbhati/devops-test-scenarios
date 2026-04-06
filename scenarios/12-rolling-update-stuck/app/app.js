const express = require("express");

const app = express();
const port = process.env.PORT || 8080;

let ready = false;

// Simulate application becoming unhealthy
setTimeout(() => {
  ready = false;
}, 5000);

app.get("/", (req, res) => {
  res.json({
    service: "scenario-12",
    message: "Rolling update stuck demo"
  });
});

app.get("/health", (req, res) => {
  res.send("OK");
});

app.get("/ready", (req, res) => {
  if (ready) {
    res.send("READY");
  } else {
    res.status(500).send("NOT READY");
  }
});

app.listen(port, "0.0.0.0", () => {
  console.log(`Server running on port ${port}`);
});
