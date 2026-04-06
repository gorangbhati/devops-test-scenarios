const express = require("express");
const axios = require("axios");

const app = express();
const port = process.env.PORT || 8080;

const BACKEND_URL = "http://scenario-15-backend:8080";

app.get("/", async (req, res) => {
  try {
    const response = await axios.get(BACKEND_URL);
    res.json({
      frontend: "ok",
      backend_response: response.data
    });
  } catch (error) {
    res.status(500).json({
      frontend: "ok",
      error: "Cannot reach backend service",
      details: error.message
    });
  }
});

app.listen(port, "0.0.0.0", () => {
  console.log(`Frontend running on port ${port}`);
});
