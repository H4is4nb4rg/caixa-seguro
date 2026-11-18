import { inject } from '@angular/core';
import { Router, Routes } from '@angular/router';
import { ApiService } from './servicos/api.service';
import { LoginPagina } from './paginas/login';
import { InicioPagina } from './paginas/inicio';
import { MovimentacaoPagina } from './paginas/movimentacao';
import { ConfirmacaoPagina, FechamentoPagina } from './paginas/resultado';

const autenticado = () => (inject(ApiService).usuario() ? true : inject(Router).parseUrl('/login'));

export const routes: Routes = [
  { path: 'login', component: LoginPagina, title: 'Entrar · Caixa Seguro' },
  { path: 'inicio', component: InicioPagina, canActivate: [autenticado], title: 'Início · Caixa Seguro' },
  { path: 'movimentacao', component: MovimentacaoPagina, canActivate: [autenticado], title: 'Nova movimentação · Caixa Seguro' },
  { path: 'confirmacao', component: ConfirmacaoPagina, canActivate: [autenticado], title: 'Registrado · Caixa Seguro' },
  { path: 'fechamento', component: FechamentoPagina, canActivate: [autenticado], title: 'Fechamento · Caixa Seguro' },
  { path: '', pathMatch: 'full', redirectTo: 'inicio' },
  { path: '**', redirectTo: 'inicio' },
];
