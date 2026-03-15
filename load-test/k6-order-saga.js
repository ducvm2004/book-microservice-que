// ADDED-ASSIGNMENT06: load testing script for gateway + saga order creation flow.
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    steady_orders: {
      executor: "constant-vus",
      vus: 10,
      duration: "60s",
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<1200"],
    http_req_failed: ["rate<0.05"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8004";

export default function () {
  const payload = JSON.stringify({
    customer_id: 1,
    simulate_payment_fail: false,
    simulate_shipping_fail: false,
  });

  const headers = { "Content-Type": "application/json" };
  const response = http.post(`${BASE_URL}/orders/`, payload, { headers });

  check(response, {
    "order created accepted": (r) => r.status === 202,
  });

  sleep(1);
}
