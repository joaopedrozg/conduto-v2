import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Credenciais {
  tipo: string;
  host: string;
  port: string;
  user: string;
  password: string;
  database: string;
  schema: string;
}

export interface Sgbd {
  tipo: string;
  nome: string;
  driver: string;
  host_padrao: string;
  porta_padrao: string;
  banco_padrao: string;
  usuario_padrao: string;
}

export interface ConexaoSalva {
  id: string;
  apelido: string;
  credenciais: Credenciais;
}

/** Frequências prontas (o backend aceita o preset ou cron de 5 campos). */
export const CRON_PRESETS = [
  { id: '15min', rotulo: 'A cada 15 minutos', cron: '*/15 * * * *' },
  { id: 'hora', rotulo: 'Hora em hora', cron: '0 * * * *' },
  { id: 'diario', rotulo: 'Diário (meia-noite)', cron: '0 0 * * *' },
  { id: 'semanal', rotulo: 'Semanal (domingo)', cron: '0 0 * * 0' },
  { id: 'custom', rotulo: 'Personalizado...', cron: '' },
];

/** Espelho em TS dos endpoints FastAPI (contrato em src/conduto/web). */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);

  sgbds(): Observable<Sgbd[]> {
    return this.http.get<Sgbd[]>('/api/sgbds');
  }

  pastas(caminho: string): Observable<{ atual: string; pai: string | null; pastas: string[]; casa: string; servidor_cwd: string }> {
    return this.http.get<{ atual: string; pai: string | null; pastas: string[]; casa: string; servidor_cwd: string }>(
      '/api/sistema/pastas',
      { params: { caminho } },
    );
  }

  testar(credenciais: Credenciais): Observable<{ ok: boolean; mensagem: string }> {
    return this.http.post<{ ok: boolean; mensagem: string }>('/api/conexoes/testar', {
      credenciais,
    });
  }

  bancos(credenciais: Credenciais): Observable<{ bancos: string[] }> {
    return this.http.post<{ bancos: string[] }>('/api/catalogo/bancos', { credenciais });
  }

  schemas(credenciais: Credenciais): Observable<{ schemas: string[] }> {
    return this.http.post<{ schemas: string[] }>('/api/catalogo/schemas', { credenciais });
  }

  tabelas(credenciais: Credenciais, schemas: string[] = []): Observable<{ tabelas: { schema: string; table: string }[] }> {
    return this.http.post<{ tabelas: { schema: string; table: string }[] }>(
      '/api/catalogo/tabelas',
      { credenciais, schemas },
    );
  }

  criarProjeto(pedido: object): Observable<object> {
    return this.http.post('/api/projeto/init', pedido);
  }

  resumo(project_dir: string): Observable<object> {
    return this.http.get('/api/projeto/resumo', { params: { project_dir } });
  }

  ddl(project_dir: string, aplicar: boolean): Observable<{ ddl: string; comandos: number; aplicados: number }> {
    return this.http.post<{ ddl: string; comandos: number; aplicados: number }>('/api/projeto/ddl', {
      project_dir,
      aplicar,
    });
  }

  schedules(project_dir: string, cron?: string): Observable<object> {
    return this.http.post('/api/projeto/schedules', { project_dir, cron });
  }

  inferir(project_dir: string, tabela?: string): Observable<object> {
    return this.http.post('/api/projeto/inferir', { project_dir, tabela });
  }

  driversFaltantes(tipo: string): Observable<{ tipo: string; faltantes: string[]; requisicoes: string[] }> {
    return this.http.get<{ tipo: string; faltantes: string[]; requisicoes: string[] }>(
      '/api/drivers/faltantes',
      { params: { tipo } },
    );
  }

  instalarDrivers(tipo: string): Observable<{ ok: boolean; mensagem: string }> {
    return this.http.post<{ ok: boolean; mensagem: string }>('/api/drivers/instalar', {
      tipo,
    });
  }

  odbcStatus(): Observable<{ instalados: string[]; ok: boolean; requeridos: string[] }> {
    return this.http.get<{ instalados: string[]; ok: boolean; requeridos: string[] }>(
      '/api/drivers/sqlserver-odbc',
    );
  }

  instalarOdbc(): Observable<{ ok: boolean; mensagem: string }> {
    return this.http.post<{ ok: boolean; mensagem: string }>(
      '/api/drivers/sqlserver-odbc/instalar',
      {},
    );
  }

  conexoesSalvas(): Observable<{ conexoes: ConexaoSalva[] }> {
    return this.http.get<{ conexoes: ConexaoSalva[] }>('/api/conexoes/salvas');
  }

  salvarConexao(apelido: string, credenciais: Credenciais): Observable<ConexaoSalva> {
    return this.http.post<ConexaoSalva>('/api/conexoes/salvas', { apelido, credenciais });
  }

  excluirConexao(id: string): Observable<{ ok: boolean }> {
    return this.http.delete<{ ok: boolean }>(`/api/conexoes/salvas/${id}`);
  }

  dagsterStatus(project_dir: string): Observable<{ rodando: boolean; responde: boolean; externo: boolean; pid: number | null; url: string }> {
    return this.http.get<{ rodando: boolean; responde: boolean; externo: boolean; pid: number | null; url: string }>(
      '/api/servidores/dagster',
      { params: { project_dir } },
    );
  }

  dagsterIniciar(project_dir: string): Observable<{ rodando: boolean; pid: number; url: string }> {
    return this.http.post<{ rodando: boolean; pid: number; url: string }>(
      '/api/servidores/dagster/iniciar',
      { project_dir },
    );
  }

  dagsterParar(project_dir: string): Observable<{ rodando: boolean }> {
    return this.http.post<{ rodando: boolean }>('/api/servidores/dagster/parar', {
      project_dir,
    });
  }
}
