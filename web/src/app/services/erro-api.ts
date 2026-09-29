/** Traduz HttpErrorResponse em mensagem legível (backend fora do ar vs. erro da API). */
export function backendIndisponivel(e: unknown): boolean {
  const status = (e as { status?: number })?.status;
  const detalhe = (e as { error?: { detail?: unknown } })?.error?.detail;
  return status === 0 || (status === 500 && detalhe == null);
}

export function mensagemErroApi(e: unknown): string {
  const err = e as { error?: { detail?: unknown }; message?: string };
  const detalhe = err?.error?.detail;
  if (typeof detalhe === 'string' && detalhe) return detalhe;
  if (err?.message) return err.message;
  return 'erro desconhecido';
}

export const DICA_BACKEND_OFF =
  'Backend indisponível (verifique se o `conduto web` está rodando na porta 8080).';

export function notificarErro(
  toast: { erro(m: string): void },
  e: unknown,
  prefixo: string,
): void {
  toast.erro(backendIndisponivel(e) ? DICA_BACKEND_OFF : `${prefixo}: ${mensagemErroApi(e)}`);
}
