// Small hand-written sample for scanner fixtures. Intentionally vulnerable. Not a real app.
const express = require("express");
const { exec } = require("child_process");
const crypto = require("crypto");
const app = express();

app.get("/hello", (req, res) => {
  // reflected output of user input
  res.send("<h1>Hello " + req.query.name + "</h1>");
});

app.get("/ping", (req, res) => {
  exec("ping -c 1 " + req.query.host, (err, out) => {
    res.send(out);
  });
});

app.get("/calc", (req, res) => {
  const result = eval(req.query.expr);
  res.json({ result });
});

app.get("/token", (req, res) => {
  const t = crypto.createHash("md5").update(req.query.user).digest("hex");
  res.json({ t });
});

app.get("/redirect", (req, res) => {
  res.redirect(req.query.to);
});

app.listen(3000);
