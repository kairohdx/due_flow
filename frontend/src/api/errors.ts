export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiErrorFromResponse(
  response: Response,
): Promise<ApiError> {
  let detail = "Não foi possível concluir a solicitação.";
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") detail = payload.detail;
  } catch {
    // A resposta pode não conter JSON.
  }
  return new ApiError(detail, response.status, detail);
}

export function userFacingError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "E-mail ou senha inválidos.";
    if (error.status === 403) return "Você não tem acesso a esta ação.";
    return error.detail;
  }
  if (error instanceof DOMException && error.name === "AbortError") {
    return "A API demorou mais que o esperado para responder.";
  }
  if (error instanceof TypeError) {
    return "Não foi possível conectar à API. Verifique se ela está em execução.";
  }
  return "Algo deu errado. Tente novamente.";
}
