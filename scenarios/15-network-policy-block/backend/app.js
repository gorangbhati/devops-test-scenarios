const express = require("express");

const app = express();
const port = process.env.PORT || 8080;

app.get("/", (req, res) => {
  res.json({
    service: "backend",
    status: "ok"
  });
});

app.listen(port, "0.0.0.0", () => {
  console.log(`Backend running on port ${port}`);
});
