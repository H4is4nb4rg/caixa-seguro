import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, Movimentacao, NOMES_PERFIL, mensagemDeErro, normalizarValor, reais } from '../servicos/api.service';

const TIPOS = [
  { id: 'venda', nome: 'Venda' }, { id: 'desconto', nome: 'Desconto' }, { id: 'troca', nome: 'Troca' },
  { id: 'sangria', nome: 'Sangria' }, { id: 'pagamento', nome: 'Pagamento' },
];
const FORMAS = [
  { id: 'dinheiro', nome: 'Dinheiro' }, { id: 'pix', nome: 'PIX' }, { id: 'debito', nome: 'Débito' }, { id: 'credito', nome: 'Crédito' },
];

@Component({
  selector: 'app-movimentacao',
  imports: [FormsModule, DatePipe],
  template: `
  <div class="tela">
    <header class="topbar">
      <button class="btn-ghost" (click)="router.navigateByUrl('/inicio')">‹ Voltar</button>
      <div style="flex:1"><div class="titulo">Nova movimentação</div><div class="usuario">{{ api.usuario()?.nome }} · Perfil {{ perfil() }}</div></div>
    </header>
    <main class="conteudo">
      <fieldset style="border:0">
        <legend class="rotulo">Tipo</legend>
        <div class="grade g3">
          @for (t of tipos; track t.id) {
            <button type="button" class="opcao" [attr.aria-pressed]="tipo() === t.id" (click)="tipo.set(t.id)">
              @if (tipo() === t.id) { ✓ } {{ t.nome }}</button>
          }
        </div>
      </fieldset>

      <div>
        <label class="rotulo" for="valor">Valor (R$)</label>
        <input id="valor" class="campo" [class.erro]="erroValor()" inputmode="decimal" placeholder="Ex.: 89,90"
               [(ngModel)]="valor" [attr.aria-invalid]="!!erroValor()" aria-describedby="valor-ajuda valor-erro">
        <div class="ajuda" id="valor-ajuda"><span>Use o teclado numérico. Ex.: 89,90</span></div>
        @if (erroValor()) { <p class="msg-erro" id="valor-erro" role="alert">⚠ {{ erroValor() }}</p> }
      </div>

      @if (exigeForma()) {
        <fieldset style="border:0">
          <legend class="rotulo">Forma de pagamento</legend>
          <div class="grade g2">
            @for (f of formas; track f.id) {
              <button type="button" class="opcao" [attr.aria-pressed]="forma() === f.id" (click)="forma.set(f.id)">
                @if (forma() === f.id) { ✓ } {{ f.nome }}</button>
            }
          </div>
          @if (erroForma()) { <p class="msg-erro" role="alert">⚠ {{ erroForma() }}</p> }
        </fieldset>
      }

      <div>
        <label class="rotulo" for="obs">Observação (opcional)</label>
        <textarea id="obs" class="campo" maxlength="200" [(ngModel)]="observacao" placeholder="Ex.: cliente levou 2 peças"></textarea>
        <div class="ajuda"><span></span><span>{{ observacao.length }}/200</span></div>
      </div>

      @if (erroGeral()) { <p class="msg-erro" role="alert">⚠ {{ erroGeral() }}</p> }

      <section class="card" aria-labelledby="ultimas">
        <h2 id="ultimas">Últimas movimentações</h2>
        @for (m of lista(); track m.id) {
          <div class="mov" [class.cancelada]="m.cancelada">
            <div>
              <div class="t">{{ nomeTipo(m.tipo) }} · {{ reais(m.valor) }}</div>
              <div class="muted">{{ m.registrado_em | date:'HH:mm' }} · por {{ m.responsavel }}
                @if (m.cancelada) { · <b>cancelada</b>: {{ m.motivo_cancelamento }} }</div>
            </div>
            @if (!m.cancelada && podeCancelar()) { <button class="btn-peq" (click)="cancelar(m)">Cancelar</button> }
          </div>
        } @empty { <p class="muted">Nenhuma movimentação ainda.</p> }
        <p class="muted" style="margin-top:8px">Para corrigir, cancele informando o motivo. Movimentações não podem ser excluídas.</p>
      </section>
    </main>
    <div class="rodape"><button class="btn primario" [disabled]="enviando()" (click)="confirmar()">✓ Confirmar</button></div>
  </div>`,
})
export class MovimentacaoPagina implements OnInit {
  api = inject(ApiService);
  router = inject(Router);
  reais = reais;
  tipos = TIPOS;
  formas = FORMAS;
  tipo = signal('venda');
  forma = signal<string | null>(null);
  valor = '';
  observacao = '';
  lista = signal<Movimentacao[]>([]);
  erroValor = signal('');
  erroForma = signal('');
  erroGeral = signal('');
  enviando = signal(false);
  perfil = computed(() => { const u = this.api.usuario(); return u ? NOMES_PERFIL[u.perfil] : ''; });
  exigeForma = computed(() => ['venda', 'troca', 'pagamento'].includes(this.tipo()));
  podeCancelar = computed(() => ['proprietaria', 'caixa'].includes(this.api.usuario()?.perfil ?? ''));

  ngOnInit() { this.carregar(); }

  carregar() {
    this.api.movimentacoes().subscribe({ next: (l) => this.lista.set(l), error: (e) => this.erroGeral.set(mensagemDeErro(e)) });
  }

  nomeTipo(id: string) { return TIPOS.find((t) => t.id === id)?.nome ?? id; }

  confirmar() {
    this.erroValor.set(''); this.erroForma.set(''); this.erroGeral.set('');
    const valor = normalizarValor(this.valor);
    if (valor === null || Number(valor) <= 0) { this.erroValor.set('Informe um valor maior que zero.'); return; }
    if (this.tipo() === 'venda' && !this.forma()) { this.erroForma.set('Escolha a forma de pagamento.'); return; }
    this.enviando.set(true);
    this.api.registrar({
      id: crypto.randomUUID(), tipo: this.tipo(), valor,
      forma_pagamento: this.exigeForma() ? this.forma() : null,
      observacao: this.observacao.trim() || null,
    }).subscribe({
      next: (r) => { this.api.ultimoRegistro.set(r); this.router.navigateByUrl('/confirmacao'); },
      error: (e) => { this.erroGeral.set(mensagemDeErro(e)); this.enviando.set(false); },
    });
  }

  cancelar(m: Movimentacao) {
    const motivo = window.prompt(`Motivo do cancelamento de ${this.nomeTipo(m.tipo)} ${reais(m.valor)}:`);
    if (!motivo || motivo.trim().length < 3) return;
    this.api.cancelar(m.id, motivo.trim()).subscribe({ next: () => this.carregar(), error: (e) => this.erroGeral.set(mensagemDeErro(e)) });
  }
}
