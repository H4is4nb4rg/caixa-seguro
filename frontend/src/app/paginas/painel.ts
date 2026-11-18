import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService, Painel, mensagemDeErro, reais } from '../servicos/api.service';

const NOMES_FORMA: Record<string, string> = { dinheiro: 'Dinheiro', pix: 'PIX', debito: 'Débito', credito: 'Crédito', outros: 'Outros' };

@Component({
  selector: 'app-painel',
  imports: [DatePipe],
  template: `
  <div class="tela">
    <header class="topbar">
      <button class="btn-ghost" (click)="router.navigateByUrl('/inicio')">‹ Início</button>
      <div style="flex:1"><div class="titulo">Painel da loja</div><div class="usuario">{{ api.usuario()?.nome }} · Perfil Proprietária</div></div>
    </header>
    <main class="conteudo">
      @if (painel(); as p) {
        @if (p.caixa_atual; as c) {
          @if (c.status === 'aberto') {
            <div class="estado ok" role="status"><span class="icone" aria-hidden="true">🔓</span>
              <div>Caixa aberto<span class="sub">desde {{ c.aberto_em | date:'HH:mm' }}</span></div></div>
          } @else {
            <div class="estado neutro" role="status"><span class="icone" aria-hidden="true">🔒</span>
              <div>Caixa fechado<span class="sub">às {{ c.fechado_em | date:'HH:mm' }} do dia {{ c.fechado_em | date:'dd/MM' }}</span></div></div>
          }
        }

        <section class="card" aria-labelledby="t-vendas">
          <h2 id="t-vendas">Vendas do caixa atual</h2>
          <div class="linha"><span>Total vendido</span><span class="grande">{{ reais(p.total_vendas) }}</span></div>
          <div class="linha"><span>Número de vendas</span><b>{{ p.quantidade_vendas }}</b></div>
          <div class="linha"><span>Dinheiro esperado na gaveta</span><b>{{ reais(p.saldo_esperado_dinheiro) }}</b></div>
          <div class="linha"><span>Movimentações canceladas</span><b>{{ p.quantidade_canceladas }}</b></div>
        </section>

        <section class="card" aria-labelledby="t-forma">
          <h2 id="t-forma">Vendas por forma de pagamento</h2>
          @for (f of p.por_forma_pagamento; track f.chave) {
            <div class="linha"><span>{{ nomeForma(f.chave) }} · {{ f.quantidade }} {{ f.quantidade === 1 ? 'venda' : 'vendas' }}</span><b>{{ reais(f.total) }}</b></div>
          } @empty { <p class="muted">Nenhuma venda ainda.</p> }
        </section>

        <section class="card" aria-labelledby="t-resp">
          <h2 id="t-resp">Movimentações por responsável</h2>
          @for (r of p.por_responsavel; track r.chave) {
            <div class="linha"><span>{{ r.chave }} · {{ r.quantidade }} {{ r.quantidade === 1 ? 'registro' : 'registros' }}</span><b>{{ reais(r.total) }}</b></div>
          } @empty { <p class="muted">Nenhuma movimentação ainda.</p> }
        </section>

        <section class="card" aria-labelledby="t-dif">
          <h2 id="t-dif">Fechamentos com diferença</h2>
          @for (c of p.caixas_com_diferenca; track c.id) {
            <div class="estado alerta" style="margin-top:8px"><span class="icone" aria-hidden="true">⚠</span>
              <div>{{ c.fechado_em | date:'dd/MM HH:mm' }} · Diferença: {{ reais(abs(c.divergencia)) }} {{ num(c.divergencia) < 0 ? 'faltando' : 'sobrando' }}
                <span class="sub">Justificativa: {{ c.justificativa }}</span></div></div>
          } @empty {
            <div class="estado ok"><span class="icone" aria-hidden="true">✔</span><div>Nenhuma diferença registrada</div></div>
          }
        </section>
        <button class="btn secundario" (click)="carregar()">↻ Atualizar</button>
      } @else {
        <p class="muted" role="status">{{ erro() || 'Carregando...' }}</p>
      }
    </main>
  </div>`,
})
export class PainelPagina implements OnInit {
  api = inject(ApiService);
  router = inject(Router);
  reais = reais;
  painel = signal<Painel | null>(null);
  erro = signal('');
  abs = (v: string | null) => Math.abs(Number(v ?? 0));
  num = (v: string | null) => Number(v ?? 0);
  nomeForma = (k: string) => NOMES_FORMA[k] ?? k;

  ngOnInit() { this.carregar(); }

  carregar() {
    this.api.painel().subscribe({ next: (p) => this.painel.set(p), error: (e) => this.erro.set(mensagemDeErro(e)) });
  }
}
