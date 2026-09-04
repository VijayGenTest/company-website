const request = require("supertest");
const app = require("../src/server");

describe("POST /api/contact", () => {
  it("should reject empty body with 400", async () => {
    const res = await request(app).post("/api/contact").send({});
    expect(res.statusCode).toBe(400);
    expect(res.body.success).toBe(false);
  });

  it("should reject invalid email", async () => {
    const res = await request(app).post("/api/contact").send({
      full_name: "Test User", email: "not-an-email", subject: "Test", message: "Test message here", captcha_token: "token"
    });
    expect(res.statusCode).toBe(400);
  });

  it("GET /health returns ok", async () => {
    const res = await request(app).get("/health");
    expect(res.statusCode).toBe(200);
    expect(res.body.status).toBe("ok");
  });
});
