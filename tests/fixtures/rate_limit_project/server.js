const express = require("express");

const app = express();

app.post("/api/login", (req, res) => {
  res.send("ok");
});

app.get("/api/status", (req, res) => {
  res.send("ok");
});
