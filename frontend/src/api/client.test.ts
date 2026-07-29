import { setAuthSession } from "../auth/authStore";
import { apiFetch, refreshAccessTokenOnce } from "./client";

it("coordena um único refresh para respostas 401 concorrentes", async () => {
  setAuthSession("token-antigo");
  let refreshCalls = 0;
  let resourceCalls = 0;

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        refreshCalls += 1;
        await Promise.resolve();
        return Response.json({
          access_token: "token-novo",
          token_type: "bearer",
          expires_in: 900,
        });
      }
      resourceCalls += 1;
      const headers = new Headers(init?.headers);
      if (headers.get("Authorization") === "Bearer token-novo") {
        return Response.json({ ok: true });
      }
      return Response.json({ detail: "não autenticado" }, { status: 401 });
    }),
  );

  const [first, second] = await Promise.all([
    apiFetch<{ ok: boolean }>("/customers"),
    apiFetch<{ ok: boolean }>("/charges"),
  ]);

  expect(first.ok).toBe(true);
  expect(second.ok).toBe(true);
  expect(refreshCalls).toBe(1);
  expect(resourceCalls).toBe(4);
});

it("compartilha a renovação usada pelo bootstrap em chamadas simultâneas", async () => {
  let refreshCalls = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      refreshCalls += 1;
      await Promise.resolve();
      return Response.json({
        access_token: "token-bootstrap",
        token_type: "bearer",
        expires_in: 900,
      });
    }),
  );

  const [first, second] = await Promise.all([
    refreshAccessTokenOnce(),
    refreshAccessTokenOnce(),
  ]);

  expect(first).toBe("token-bootstrap");
  expect(second).toBe("token-bootstrap");
  expect(refreshCalls).toBe(1);
});
