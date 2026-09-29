import { Routes } from '@angular/router';
import { CriarComponent } from './pages/criar.component';
import { AdminShellComponent } from './pages/admin/admin-shell.component';
import { VisaoComponent } from './pages/admin/visao.component';
import { DdlComponent } from './pages/admin/ddl.component';
import { SchedulesComponent } from './pages/admin/schedules.component';
import { InferirComponent } from './pages/admin/inferir.component';
import { ServidoresComponent } from './pages/admin/servidores.component';
import { DriversComponent } from './pages/admin/drivers.component';

export const routes: Routes = [
  { path: '', redirectTo: 'criar', pathMatch: 'full' },
  { path: 'criar', component: CriarComponent },
  {
    path: 'admin',
    component: AdminShellComponent,
    children: [
      { path: '', redirectTo: 'visao', pathMatch: 'full' },
      { path: 'visao', component: VisaoComponent },
      { path: 'ddl', component: DdlComponent },
      { path: 'schedules', component: SchedulesComponent },
      { path: 'inferir', component: InferirComponent },
      { path: 'servidores', component: ServidoresComponent },
      { path: 'drivers', component: DriversComponent },
    ],
  },
];
