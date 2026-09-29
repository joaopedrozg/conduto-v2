import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ToastService } from '../../services/toast.service';
import { notificarErro } from '../../services/erro-api';

@Component({
  selector: 'conduto-admin-drivers',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2>Drivers</h2>
      <label>SGBD</label>
      <select [(ngModel)]="driverTipo">
        <option value="postgresql">PostgreSQL</option>
        <option value="mysql">MySQL</option>
        <option value="sqlserver">SQL Server</option>
        <option value="clickhouse">ClickHouse</option>
        <option value="duckdb">DuckDB</option>
        <option value="deltalake">Delta Lake</option>
      </select>
      <button (click)="verificar()">Verificar drivers</button>
      <button (click)="instalar()">Instalar drivers (pip no servidor)</button>
      <button class="secundario" (click)="verOdbc()">Status ODBC SQL Server</button>
      <button class="secundario" (click)="instalarOdbc()">Instalar ODBC SQL Server</button>
    </div>
  `,
})
export class DriversComponent {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  driverTipo = 'sqlserver';

  verificar(): void {
    this.api.driversFaltantes(this.driverTipo).subscribe({
      next: (r) => {
        if (r.faltantes.length) this.toast.erro(`Drivers ausentes (${r.tipo}): ${r.faltantes.join(', ')}.`);
        else this.toast.ok(`Drivers de ${r.tipo} OK.`);
      },
      error: (e) => notificarErro(this.toast, e, 'Drivers'),
    });
  }

  instalar(): void {
    this.toast.info(`Instalando drivers de ${this.driverTipo} no servidor...`);
    this.api.instalarDrivers(this.driverTipo).subscribe({
      next: (r) => this.toast.ok(r.mensagem),
      error: (e) => notificarErro(this.toast, e, 'Instalação'),
    });
  }

  verOdbc(): void {
    this.api.odbcStatus().subscribe({
      next: (r) => {
        if (r.ok) this.toast.ok(`ODBC OK: ${r.instalados.join(', ')}`);
        else this.toast.erro('ODBC do SQL Server ausente no servidor.');
      },
      error: (e) => notificarErro(this.toast, e, 'ODBC'),
    });
  }

  instalarOdbc(): void {
    this.toast.info('Instalando ODBC Driver do SQL Server no servidor...');
    this.api.instalarOdbc().subscribe({
      next: (r) => this.toast.ok(r.mensagem),
      error: (e) => notificarErro(this.toast, e, 'ODBC'),
    });
  }
}
