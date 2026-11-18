import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export type Perfil = 'proprietaria' | 'caixa' | 'vendedora';

export interface Usuario { id: string; nome: string; login: string; perfil: Perfil; ativo: boolean; }
export interface Caixa {
  id: string; status: 'aberto' | 'fechado'; valor_inicial: string; aberto_em: string;
  fechado_em?: string | null; valor_esperado?: string | null; valor_contado?: string | null;
  divergencia?: string | null; justificativa?: string | null;
}
export interface Resumo { caixa: Caixa | null; saldo_esperado: string | null; quantidade_movimentacoes: number; }
export interface Movimentacao {
  id: string; tipo: string; valor: string; forma_pagamento: string | null; observacao: string | null;
  registrado_em: string; responsavel: string; cancelada: boolean; motivo_cancelamento: string | null;
}
export interface TotalPorChave { chave: string; quantidade: number; total: string; }
export interface CaixaPainel { id: string; status: string; aberto_em: string; fechado_em: string | null; divergencia: string | null; justificativa: string | null; }
export interface Painel {
  caixa_atual: CaixaPainel | null; total_vendas: string; quantidade_vendas: number; saldo_esperado_dinheiro: string | null;
  quantidade_canceladas: number; por_forma_pagamento: TotalPorChave[]; por_responsavel: TotalPorChave[]; caixas_com_diferenca: CaixaPainel[];
}
export interface Registro { movimentacao: Movimentacao; saldo_esperado: string; }

const CHAVE_SESSAO = 'caixa_seguro_sessao';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiUrl;

  readonly usuario = signal<Usuario | null>(null);
  private token: string | null = null;
  ultimoRegistro = signal<Registro | null>(null);

  constructor() {
    const salvo = sessionStorage.getItem(CHAVE_SESSAO);
    if (salvo) {
      const { token, usuario } = JSON.parse(salvo);
      this.token = token;
      this.usuario.set(usuario);
    }
  }

  private get opcoes() {
    const headers = this.token ? new HttpHeaders({ Authorization: `Bearer ${this.token}` }) : undefined;
    return { headers, withCredentials: true };
  }

  login(login: string, senha: string): Observable<{ access_token: string; usuario: Usuario }> {
    return this.http.post<{ access_token: string; usuario: Usuario }>(`${this.base}/auth/login`, { login, senha }, { withCredentials: true });
  }

  iniciarSessao(token: string, usuario: Usuario) {
    this.token = token;
    this.usuario.set(usuario);
    sessionStorage.setItem(CHAVE_SESSAO, JSON.stringify({ token, usuario }));
  }

  encerrarSessao() {
    this.token = null;
    this.usuario.set(null);
    sessionStorage.removeItem(CHAVE_SESSAO);
  }

  logout() { return this.http.post(`${this.base}/auth/logout`, {}, this.opcoes); }
  resumo() { return this.http.get<Resumo>(`${this.base}/caixa/atual`, this.opcoes); }
  abrir(valor_inicial: string) { return this.http.post<Caixa>(`${this.base}/caixa/abrir`, { valor_inicial }, this.opcoes); }
  fechar(valor_contado: string, justificativa: string | null) {
    return this.http.post<Caixa>(`${this.base}/caixa/fechar`, { valor_contado, justificativa }, this.opcoes);
  }
  painel() { return this.http.get<Painel>(`${this.base}/caixa/painel`, this.opcoes); }
  movimentacoes() { return this.http.get<Movimentacao[]>(`${this.base}/movimentacoes?limite=10`, this.opcoes); }
  registrar(dados: { id: string; tipo: string; valor: string; forma_pagamento: string | null; observacao: string | null }) {
    return this.http.post<Registro>(`${this.base}/movimentacoes`, dados, this.opcoes);
  }
  cancelar(id: string, motivo: string) {
    return this.http.post<Registro>(`${this.base}/movimentacoes/${id}/cancelar`, { motivo }, this.opcoes);
  }
}

/** Converte erros da API em mensagens simples, sem detalhes técnicos. */
export function mensagemDeErro(erro: HttpErrorResponse): string {
  if (erro.status === 0) return 'Sem conexão com o servidor. Verifique a internet e tente novamente.';
  const detalhe = erro.error?.detail;
  if (typeof detalhe === 'string') return detalhe;
  if (erro.status === 422) return 'Confira os dados informados.';
  return 'Não foi possível concluir a operação.';
}

/** Aceita "189,90" ou "189.90" e devolve "189.90"; retorna null se inválido. */
export function normalizarValor(texto: string): string | null {
  const limpo = (texto || '').trim().replace(/\./g, '').replace(',', '.');
  if (!/^\d+(\.\d{1,2})?$/.test(limpo)) return null;
  return Number(limpo).toFixed(2);
}

export function reais(valor: string | number | null | undefined): string {
  return Number(valor ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export const NOMES_PERFIL: Record<Perfil, string> = { proprietaria: 'Proprietária', caixa: 'Caixa', vendedora: 'Vendedora' };
