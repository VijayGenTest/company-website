require("dotenv").config();
const express = require("express");
const helmet  = require("helmet");
const cors    = require("cors");
const morgan  = require("morgan");
const rateLimit = require("express-rate-limit");
const contactRouter = require("./routes/contact");
const logger  = require("./utils/logger");

const app  = express();
const PORT = process.env.NODE_PORT || 3000;

app.set("trust proxy", 1);

// SECURITY FIX [SEC-002]: Enable Helmet's Content Security Policy with a
// restrictive policy suitable for an API backend. This prevents XSS injection
// by restricting what scripts, connections, and frames are permitted.
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'none'"],
      scriptSrc:  ["'self'"],
      connectSrc: ["'self'"],
      frameSrc:   ["'none'"],
      objectSrc:  ["'none'"],
      baseUri:    ["'none'"],
    },
  },
}));
app.use(cors({ origin: process.env.ALLOWED_ORIGIN || "http://localhost" }));
app.use(express.json({ limit: "10kb" }));
app.use(express.urlencoded({ extended: true, limit: "10kb" }));
app.use(morgan("combined", { stream: { write: msg => logger.info(msg.trim()) } }));

const contactLimiter = rateLimit({
  windowMs: 60 * 60 * 1000,
  max: 10,
  message: { success: false, error: "Too many requests. Please try again later." },
  standardHeaders: true,
  legacyHeaders: false,
});

app.use("/api/contact", contactLimiter, contactRouter);
app.get("/health", (req, res) => res.json({ status: "ok", timestamp: new Date().toISOString() }));

app.use((req, res) => res.status(404).json({ error: "Not found" }));

app.use((err, req, res, next) => {
  logger.error("Unhandled error:", err);
  res.status(500).json({ success: false, error: "Internal server error" });
});

app.listen(PORT, () => logger.info(`Node.js backend running on port ${PORT}`));

module.exports = app;
