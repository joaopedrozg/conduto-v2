import { Injectable, signal } from '@angular/core';

export interface Toast {
  id: number;
  tipo: 'ok' | 'erro' | 'info';
  texto: string;
}

/** Toasts top-right com auto-dismiss (feedback transitório; detalhes ficam no log). */
@Injectable({ providedIn: 'root' })
export class ToastService {
  toasts = signal<Toast[]>([]);
  private seq = 0;

  mostrar(tipo: Toast['tipo'], texto: string, ms = 7000): void {
    const id = ++this.seq;
    this.toasts.set([...this.toasts(), { id, tipo, texto }]);
    setTimeout(() => this.fechar(id), ms);
  }

  ok(texto: string): void {
    this.mostrar('ok', texto, 5000);
  }

  info(texto: string): void {
    this.mostrar('info', texto, 5000);
  }

  erro(texto: string): void {
    this.mostrar('erro', texto, 10000);
  }

  fechar(id: number): void {
    this.toasts.set(this.toasts().filter((t) => t.id !== id));
  }
}
