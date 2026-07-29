import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import { resetAuthStateForTests } from "../auth/authStore";
import { resetRefreshForTests } from "../api/client";

afterEach(() => {
  cleanup();
  resetAuthStateForTests();
  resetRefreshForTests();
  vi.restoreAllMocks();
});
