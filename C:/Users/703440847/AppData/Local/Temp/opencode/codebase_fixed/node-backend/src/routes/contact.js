const express   = require("express");
const { body, validationResult } = require("express-validator");
const axios     = require("axios");
const logger    = require("../utils/logger");

const router = express.Router();
const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || "http://localhost:8000";

const contactValidationRules = [
  body("full_name")
    .trim().notEmpty().withMessage("Full name is required.")
    .isLength({ min: 2, max: 100 }).withMessage("Full name must be 2-100 characters.")
    .matches(/^[a-zA-Z\s'\-]+$/).withMessage("Full name contains invalid characters."),
  body("email")
    .trim().notEmpty().withMessage("Email address is required.")
    .isEmail().withMessage("Please provide a valid email address.")
    .normalizeEmail().isLength({ max: 150 }),
  body("phone")
    .optional({ checkFalsy: true }).trim()
    .isMobilePhone("any").withMessage("Please provide a valid phone number."),
  body("subject")
    .trim().notEmpty().withMessage("Subject is required.")
    .isLength({ min: 3, max: 200 }).withMessage("Subject must be 3-200 characters."),
  body("message")
    .trim().notEmpty().withMessage("Message is required.")
    .isLength({ min: 10, max: 2000 }).withMessage("Message must be 10-2000 characters."),
  body("captcha_token")
    .notEmpty().withMessage("CAPTCHA token is required."),
];

router.post("/", contactValidationRules, async (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({
      success: false,
      errors: errors.array().map(e => ({ field: e.path, message: e.msg }))
    });
  }

  const { full_name, email, phone, subject, message, captcha_token } = req.body;
  const clientIp = req.ip || req.socket.remoteAddress;

  try {
    const response = await axios.post(
      `${PYTHON_SERVICE_URL}/process`,
      { full_name, email, phone: phone || null, subject, message, captcha_token, ip_address: clientIp },
      { timeout: 15000 }
    );
    logger.info(`Contact form processed for IP: ${clientIp}`);
    return res.status(200).json({
      success: true,
      message: "Thank you for your message. We will get back to you shortly.",
      submission_id: response.data.submission_id
    });
  } catch (err) {
    if (err.response) {
      const status = err.response.status;
      const data   = err.response.data;
      logger.warn(`Python service returned ${status}:`, data);
      if (status === 400) return res.status(400).json({ success: false, error: data.detail || "Invalid request." });
      if (status === 422) return res.status(422).json({ success: false, error: "CAPTCHA verification failed." });
    }
    logger.error("Error calling Python service:", err.message);
    return res.status(500).json({ success: false, error: "An error occurred. Please try again later." });
  }
});

module.exports = router;
