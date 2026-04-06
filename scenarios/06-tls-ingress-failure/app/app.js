const express = require("express");

const app = express();
const port = process.env.PORT || 8080;

app.get("/", (req, res) => {
  res.json({
    service: "scenario-06",
    status: "ok",
    message: "TLS ingress failure scenario"
  });
});

app.get("/health", (req, res) => {
  res.send("OK");
});

app.listen(port, "0.0.0.0", () => {
  console.log(`Server running on port ${port}`);
});
