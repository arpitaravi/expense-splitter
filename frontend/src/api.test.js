import { money, toPaise } from "./api";

test("money formats paise as rupees", () => {
  expect(money(123456)).toBe("₹1,234.56");
});

test("toPaise avoids float drift", () => {
  expect(toPaise("0.1") + toPaise("0.2")).toBe(30);
  expect(toPaise("19.99")).toBe(1999);
});
