import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import os

st.set_page_config(page_title="Gestão Grupo Peres", layout="wide", page_icon="🚜")

# Estilização Moderna e Responsiva
st.markdown("""
    <style>
        .hero-banner { 
            background: linear-gradient(135deg, #004d26 0%, #002e16 100%); 
            padding: 20px; 
            border-radius: 15px; 
            color: white; 
            text-align: center; 
        }
        .stButton>button { 
            width: 100%; 
            border-radius: 5px; 
            font-weight: bold; 
        }
        .logo-box {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100%;
        }
    </style>
""", unsafe_allow_html=True)

conn = sqlite3.connect('estoque_boa_vista.db', check_same_thread=False)

def init_db():
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (nome TEXT PRIMARY KEY, categoria TEXT, unidade TEXT, quantidade REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS veiculos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)''')
    
    try:
        c.execute('''ALTER TABLE veiculos ADD COLUMN detalhes TEXT''')
    except sqlite3.OperationalError:
        pass 
        
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT, nivel TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS movimentacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, setor TEXT, veiculo TEXT, qtd REAL, tipo TEXT, data TEXT, detalhes_aplicacao TEXT)''')
    
    # TABELA PARA CATEGORIAS DINÂMICAS
    c.execute('''CREATE TABLE IF NOT EXISTS categorias (nome TEXT PRIMARY KEY)''')
    c.execute("SELECT COUNT(*) FROM categorias")
    if c.fetchone()[0] == 0:
        categorias_padrao = [('Almoxarifado',), ('Defensivos',), ('Lubrificantes',), ('Combustível',)]
        c.executemany("INSERT INTO categorias (nome) VALUES (?)", categorias_padrao)

    # REMOVER APENAS O USUÁRIO 'admin' SE EXISTIR
    c.execute("DELETE FROM usuarios WHERE usuario = 'admin'")
    
    # INSERIR USUÁRIO PRINCIPAL APENAS SE NÃO EXISTIR
    c.execute("SELECT COUNT(*) FROM usuarios WHERE usuario = 'grupoperes-bv'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO usuarios VALUES ('grupoperes-bv', '55911466', 'Admin')")
    
    conn.commit()

init_db()

# =====================================================================
# ÁREA DE LOGIN (PROTEÇÃO DO SISTEMA)
# =====================================================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['usuario_logado'] = ""
    st.session_state['nivel_usuario'] = ""

if not st.session_state['logged_in']:
    st.markdown("<br><br><h1 style='text-align: center;'>🔐 Acesso ao Sistema</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("login_form"):
            user_input = st.text_input("Usuário")
            pass_input = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                c = conn.cursor()
                c.execute("SELECT * FROM usuarios WHERE usuario = ? AND senha = ?", (user_input, pass_input))
                usuario_encontrado = c.fetchone()
                if usuario_encontrado:
                    st.session_state['logged_in'] = True
                    st.session_state['usuario_logado'] = user_input
                    st.session_state['nivel_usuario'] = usuario_encontrado[2]
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")
    st.stop()

# Botão de Sair
if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state['logged_in'] = False
    st.session_state['usuario_logado'] = ""
    st.session_state['nivel_usuario'] = ""
    st.rerun()

# Mostrar usuário logado na barra lateral
st.sidebar.markdown(f"### 👤 Usuário: {st.session_state['usuario_logado']}")
st.sidebar.markdown(f"### 📊 Nível: {st.session_state['nivel_usuario']}")
st.sidebar.markdown("---")

# =====================================================================
# RESTANTE DO SISTEMA
# =====================================================================

def get_categorias():
    df = pd.read_sql("SELECT nome FROM categorias ORDER BY nome", conn)
    return df['nome'].tolist() if not df.empty else ["Geral"]

def gerar_relatorio_marcado(df, titulo):
    cabecalho = "GRUPO PERES - GESTAO DE ESTOQUE\n"
    cabecalho += "FAZENDA BOA VISTA\n"
    cabecalho += f"Relatorio: {titulo}\n"
    cabecalho += f"Data de Emissao: {datetime.now().strftime('%d/%m/%Y as %H:%M')}\n"
    cabecalho += "-" * 50 + "\n\n"
    csv_data = df.to_csv(index=False, sep=';')
    return (cabecalho + csv_data).encode('utf-8-sig')

# --- CABEÇALHO UNIFICADO ---
col_logo_esq, col_titulo, col_logo_dir = st.columns([1, 5, 1])
with col_logo_esq:
    st.markdown('<div class="logo-box"><img src="https://img.icons8.com/color/128/tractor.png" width="110"></div>', unsafe_allow_html=True)
with col_titulo:
    st.markdown('<div class="hero-banner"><h1>GRUPO PERES</h1><h3>Gestão de Estoque - Fazenda Boa Vista</h3></div>', unsafe_allow_html=True)
with col_logo_dir:
    st.markdown('<div class="logo-box"><img src="https://img.icons8.com/color/128/tractor.png" width="110" style="transform: scaleX(-1);"></div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# --- MENU DE NAVEGAÇÃO PRINCIPAL ---
if st.session_state['nivel_usuario'] == 'Admin':
    menu = st.selectbox("📂 SELECIONE O MÓDULO DO SISTEMA QUE DESEJA ACESSAR:", [
        "Início", 
        "Movimentação", 
        "Editar/Corrigir Movimentação", 
        "Configurações"
    ])
else:
    menu = st.selectbox("📂 SELECIONE O MÓDULO DO SISTEMA QUE DESEJA ACESSAR:", [
        "Início", 
        "Movimentação"
    ])

st.markdown("---")

lista_categorias_dinamica = get_categorias()

# --- ABA INÍCIO ---
if menu == "Início":
    df_estoque_dash = pd.read_sql("SELECT nome, categoria, quantidade, unidade FROM estoque", conn)
    df_movs_dash = pd.read_sql("SELECT data, tipo, item, qtd, setor FROM movimentacoes ORDER BY id DESC LIMIT 100", conn)
    df_veic_dash = pd.read_sql("SELECT nome, detalhes FROM veiculos", conn)
    
    total_itens = len(df_estoque_dash)
    total_movs_query = pd.read_sql("SELECT COUNT(*) as total FROM movimentacoes", conn)
    total_movs = total_movs_query['total'][0] if not total_movs_query.empty else 0
    total_veic = len(df_veic_dash)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📦 Itens no Inventário", total_itens)
        with st.expander("👁️ Clique aqui para ver os itens"):
            if not df_estoque_dash.empty: st.dataframe(df_estoque_dash, use_container_width=True)
    with col2:
        st.metric("🔄 Movimentações Registradas", total_movs)
        with st.expander("👁️ Clique para ver as últimas 100"):
            if not df_movs_dash.empty: st.dataframe(df_movs_dash, use_container_width=True)
    with col3:
        st.metric("🚜 Frota de Máquinas", total_veic)
        with st.expander("👁️ Clique para ver a frota detalhada"):
            if not df_veic_dash.empty: st.dataframe(df_veic_dash, use_container_width=True)

# --- MOVIMENTAÇÃO ---
elif menu == "Movimentação":
    st.header("🔄 Movimentação de Estoque")
    
    if st.session_state['nivel_usuario'] == 'Admin':
        col1, col2 = st.columns(2)
        with col1:
            setor = st.selectbox("1. Selecione a Categoria:", lista_categorias_dinamica)
        with col2:
            tipo = st.radio("2. Tipo de Operação:", ["ENTRADA", "SAÍDA"], horizontal=True)
    else:
        st.info("ℹ️ Usuários comuns podem registrar apenas SAÍDAS de estoque.")
        col1, col2 = st.columns(2)
        with col1:
            setor = st.selectbox("1. Selecione a Categoria:", lista_categorias_dinamica)
        with col2:
            tipo = "SAÍDA"
            st.markdown("**2. Tipo de Operação: SAÍDA**")

    itens_df = pd.read_sql("SELECT nome FROM estoque WHERE categoria = ? AND nome != ''", conn, params=(setor,))
    
    if not itens_df.empty:
        filtro_item = st.text_input("🔍 Pesquisar Item:", placeholder="Digite para filtrar o item desejado...", key="filtro_mov")
    else:
        filtro_item = ""
    
    with st.form("mov_form", clear_on_submit=True):
        if itens_df.empty:
            st.warning(f"⚠️ Nenhum item encontrado em '{setor}'.")
            item = None
        else:
            if filtro_item:
                itens_filtrados = [i for i in itens_df['nome'].tolist() if filtro_item.lower() in i.lower()]
                if itens_filtrados:
                    item = st.selectbox("3. Digite ou selecione o Item:", itens_filtrados)
                else:
                    st.warning(f"Nenhum item corresponde à pesquisa '{filtro_item}'")
                    item = st.selectbox("3. Digite ou selecione o Item:", itens_df['nome'].tolist())
            else:
                item = st.selectbox("3. Digite ou selecione o Item:", itens_df['nome'].tolist())
            
            qtd = st.number_input("4. Quantidade", min_value=0.01)
            detalhes_mov, veic = "", "N/A"
            
            if setor == "Defensivos":
                if tipo == "SAÍDA":
                    st.markdown("---")
                    st.markdown("### 🌱 Direcionamento da Aplicação")
                    veic = "Aplicação em Campo"
                    detalhes_mov = st.text_area("Informe o Talhão e Cultura:")
                else:
                    veic = "Estoque (Base)"
                    detalhes_mov = st.text_input("Observação (opcional):", placeholder="Descreva a entrada...")
            
            elif setor == "Almoxarifado":
                if tipo == "SAÍDA":
                    st.markdown("---")
                    st.markdown("### 🚜 Direcionamento da Saída")
                    veic_df = pd.read_sql("SELECT nome FROM veiculos", conn)
                    if veic_df.empty:
                        st.error("Nenhuma máquina cadastrada! Cadastre primeiro em Configurações > Gerenciar Máquinas.")
                        veic = "Não informada"
                    else:
                        veic = st.selectbox("Para qual Máquina/Veículo?", veic_df['nome'].tolist())
                    detalhes_mov = st.text_area("Descreva o motivo/uso do item:", placeholder="Ex: Para manutenção, troca de peça, etc.")
                else:
                    veic = "Estoque (Base)"
                    detalhes_mov = st.text_input("Observação (opcional):", placeholder="Descreva a entrada...")
            
            else:
                if tipo == "SAÍDA":
                    st.markdown("---")
                    st.markdown("### 🚜 Direcionamento da Saída")
                    veic_df = pd.read_sql("SELECT nome FROM veiculos", conn)
                    if veic_df.empty:
                        st.error("Nenhuma máquina cadastrada! Cadastre primeiro em Configurações > Gerenciar Máquinas.")
                        veic = "Não informada"
                    else:
                        veic = st.selectbox("Para qual Máquina/Veículo?", veic_df['nome'].tolist())
                    horimetro = st.number_input("Horímetro / KM Atual", value=0.0)
                    detalhes_mov = f"Horímetro/KM: {horimetro}"
                else:
                    veic = "Estoque (Base)"
                    detalhes_mov = st.text_input("Observação (opcional):", placeholder="Descreva a entrada...")
        
        if st.form_submit_button("Confirmar Operação"):
            if item:
                cursor = conn.cursor()
                cursor.execute("SELECT quantidade FROM estoque WHERE nome = ?", (item,))
                estoque_atual = cursor.fetchone()[0]
                
                if tipo == "SAÍDA" and qtd > estoque_atual:
                    st.error(f"❌ OPERAÇÃO NEGADA: Saldo insuficiente. Estoque atual: {estoque_atual}.")
                else:
                    novo_estoque = estoque_atual + qtd if tipo == "ENTRADA" else estoque_atual - qtd
                    conn.cursor().execute("UPDATE estoque SET quantidade = ? WHERE nome = ?", (novo_estoque, item))
                    conn.cursor().execute("INSERT INTO movimentacoes (item, setor, veiculo, qtd, tipo, data, detalhes_aplicacao) VALUES (?,?,?,?,?,?,?)", 
                                          (item, setor, veic, qtd, tipo, datetime.now().strftime("%Y-%m-%d"), detalhes_mov))
                    conn.commit()
                    st.success(f"✅ Operação registrada: {qtd} de {item}!")

# --- EDITAR / CORRIGIR MOVIMENTAÇÃO ---
elif menu == "Editar/Corrigir Movimentação":
    if st.session_state['nivel_usuario'] != 'Admin':
        st.error("❌ ACESSO NEGADO: Apenas administradores podem acessar esta área!")
        st.stop()
    
    st.header("🛠️ Localizar, Editar ou Excluir Movimentação")
    df_movs = pd.read_sql("SELECT id, data, tipo, item, qtd, setor, veiculo FROM movimentacoes ORDER BY id DESC LIMIT 50", conn)
    
    if df_movs.empty:
        st.warning("Nenhuma movimentação recente.")
    else:
        lista_movs = [f"ID {row['id']} | {row['data']} | {row['tipo']} | {row['qtd']}x {row['item']}" for _, row in df_movs.iterrows()]
        mov_selecionada = st.selectbox("Selecione a Movimentação:", lista_movs)
        mov_id = int(mov_selecionada.split(" | ")[0].replace("ID ", ""))
        dados_mov = pd.read_sql("SELECT * FROM movimentacoes WHERE id = ?", conn, params=(mov_id,)).iloc[0]

        with st.form("edit_mov_form"):
            st.subheader(f"Editando Registro #{mov_id}")
            col1, col2 = st.columns(2)
            with col1:
                novo_tipo = st.selectbox("Operação", ["ENTRADA", "SAÍDA"], index=["ENTRADA", "SAÍDA"].index(dados_mov['tipo']))
                nova_data = st.text_input("Data (YYYY-MM-DD)", value=dados_mov['data'])
                nova_qtd = st.number_input("Quantidade", value=float(dados_mov['qtd']), min_value=0.01)
            with col2:
                lista_itens = pd.read_sql("SELECT nome FROM estoque", conn)['nome'].tolist()
                if dados_mov['item'] not in lista_itens: lista_itens.append(dados_mov['item']) 
                novo_item = st.selectbox("Item", lista_itens, index=lista_itens.index(dados_mov['item']))
                novo_setor = st.selectbox("Setor", lista_categorias_dinamica, index=lista_categorias_dinamica.index(dados_mov['setor']) if dados_mov['setor'] in lista_categorias_dinamica else 0)

            lista_veic = pd.read_sql("SELECT nome FROM veiculos", conn)['nome'].tolist()
            opcoes_extras = ["Estoque (Base)", "Aplicação em Campo", "Não informada"]
            for op in opcoes_extras:
                if op not in lista_veic: lista_veic.insert(0, op)
            if dados_mov['veiculo'] not in lista_veic: lista_veic.append(dados_mov['veiculo'])
                
            novo_veic = st.selectbox("Veículo/Local", lista_veic, index=lista_veic.index(dados_mov['veiculo']))
            novo_detalhes = st.text_area("Detalhes", value=dados_mov['detalhes_aplicacao'])

            col_salvar, col_excluir = st.columns(2)
            with col_salvar:
                if st.form_submit_button("💾 Salvar Correção"):
                    cursor = conn.cursor()
                    try:
                        cursor.execute("SELECT quantidade FROM estoque WHERE nome = ?", (dados_mov['item'],))
                        old_stock_row = cursor.fetchone()
                        if old_stock_row:
                            estoque_revertido = old_stock_row[0] - dados_mov['qtd'] if dados_mov['tipo'] == 'ENTRADA' else old_stock_row[0] + dados_mov['qtd']
                            cursor.execute("UPDATE estoque SET quantidade = ? WHERE nome = ?", (estoque_revertido, dados_mov['item']))

                        cursor.execute("SELECT quantidade FROM estoque WHERE nome = ?", (novo_item,))
                        new_stock_row = cursor.fetchone()
                        if new_stock_row:
                            current_new_stock = new_stock_row[0]
                            if novo_tipo == 'SAÍDA' and nova_qtd > current_new_stock:
                                st.error("❌ Saldo insuficiente para corrigir esta saída.")
                                conn.rollback() 
                            else:
                                final_stock = current_new_stock + nova_qtd if novo_tipo == 'ENTRADA' else current_new_stock - nova_qtd
                                cursor.execute("UPDATE estoque SET quantidade=? WHERE nome=?", (final_stock, novo_item))
                                cursor.execute('''UPDATE movimentacoes SET item=?, setor=?, veiculo=?, qtd=?, tipo=?, data=?, detalhes_aplicacao=? WHERE id=?''',
                                              (novo_item, novo_setor, novo_veic, nova_qtd, novo_tipo, nova_data, novo_detalhes, mov_id))
                                conn.commit(); st.success("✅ Corrigido!"); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

            with col_excluir:
                if st.form_submit_button("🚨 Excluir Movimentação"):
                    cursor = conn.cursor()
                    cursor.execute("SELECT quantidade FROM estoque WHERE nome = ?", (dados_mov['item'],))
                    old_stock_row = cursor.fetchone()
                    if old_stock_row:
                        estoque_revertido = old_stock_row[0] - dados_mov['qtd'] if dados_mov['tipo'] == 'ENTRADA' else old_stock_row[0] + dados_mov['qtd']
                        cursor.execute("UPDATE estoque SET quantidade = ? WHERE nome = ?", (estoque_revertido, dados_mov['item']))
                    cursor.execute("DELETE FROM movimentacoes WHERE id = ?", (mov_id,))
                    conn.commit(); st.success("🗑️ Excluído!"); st.rerun()

# --- CONFIGURAÇÕES ---
elif menu == "Configurações":
    if st.session_state['nivel_usuario'] != 'Admin':
        st.error("❌ ACESSO NEGADO: Apenas administradores podem acessar esta área!")
        st.stop()
    
    st.header("⚙️ Central de Administração e Cadastros")
    sub_menu = st.selectbox("Selecione a ferramenta administrativa:", [
        "Cadastrar Novo Item", "Editar/Corrigir Item Existente", "Importação em Massa", 
        "Gerenciar Máquinas", "Relatório de Estoque (Exportar)", "Relatório de Movimentação (Exportar)", 
        "Gestão de Categorias do Sistema", "Controle de Usuários"
    ])
    st.markdown("---")

    if sub_menu == "Cadastrar Novo Item":
        st.subheader("📦 Cadastro Individual de Insumos")
        with st.form("c_item", clear_on_submit=True):
            nome = st.text_input("Nome do Item (Obrigatório)*")
            cat = st.selectbox("Categoria", lista_categorias_dinamica)
            uni = st.selectbox("Unidade", ["Unidade", "Litros", "KG", "Balde", "Gramas", "Caixa"])
            qtd = st.number_input("Estoque Inicial", min_value=0.0)
            if st.form_submit_button("Registrar Item"):
                if not nome.strip(): st.error("❌ ERRO: O nome do item é obrigatório!")
                else:
                    conn.cursor().execute("INSERT OR REPLACE INTO estoque VALUES (?,?,?,?)", (nome.strip(), cat, uni, qtd))
                    conn.commit(); st.success(f"✅ Item '{nome}' registrado!")

    elif sub_menu == "Editar/Corrigir Item Existente":
        st.subheader("🛠️ Localizar, Editar ou Excluir Item")
        setor_edit = st.selectbox("1. Selecione a Categoria do item:", lista_categorias_dinamica)
        itens_df = pd.read_sql("SELECT * FROM estoque WHERE categoria = ?", conn, params=(setor_edit,))
        if itens_df.empty: st.warning(f"Nenhum item em {setor_edit}.")
        else:
            lista_nomes = [n if n.strip() else "[ITEM SEM NOME]" for n in itens_df['nome'].tolist()]
            nome_selecionado_display = st.selectbox("2. Selecione o Item para edição:", lista_nomes)
            nome_real = "" if nome_selecionado_display == "[ITEM SEM NOME]" else nome_selecionado_display
            dados_atuais = itens_df[itens_df['nome'] == nome_real].iloc[0]
            with st.form("edit_item_form"):
                novo_nome = st.text_input("Nome do Item", value=nome_selecionado_display)
                nova_cat = st.selectbox("Atualizar Categoria", lista_categorias_dinamica, index=lista_categorias_dinamica.index(dados_atuais['categoria']) if dados_atuais['categoria'] in lista_categorias_dinamica else 0)
                nova_qtd = st.number_input("Ajuste de Saldo", value=float(dados_atuais['quantidade']), min_value=0.0)
                if st.form_submit_button("Salvar Alterações"):
                    conn.cursor().execute("UPDATE estoque SET nome=?, categoria=?, quantidade=? WHERE nome=?", (novo_nome, nova_cat, nova_qtd, nome_real))
                    conn.commit(); st.success("✅ Item atualizado!"); st.rerun()

    elif sub_menu == "Importação em Massa":
        st.subheader("📥 Importação em Massa")
        df_modelo = pd.DataFrame(columns=["Nome", "Categoria", "Unidade", "Quantidade"])
        st.download_button("1️⃣ Baixar Planilha Modelo", df_modelo.to_csv(index=False, sep=';').encode('utf-8-sig'), "modelo.csv", "text/csv")
        arquivo_upload = st.file_uploader("2️⃣ Carregar arquivo CSV", type=["csv"])
        if arquivo_upload:
            df_import = pd.read_csv(arquivo_upload, sep=';')
            if st.button("Confirmar Importação"):
                for _, row in df_import.iterrows():
                    conn.cursor().execute("INSERT OR REPLACE INTO estoque VALUES (?,?,?,?)", (row['Nome'], row['Categoria'], row['Unidade'], row['Quantidade']))
                conn.commit(); st.success("Importado!")

    elif sub_menu == "Gerenciar Máquinas":
        st.subheader("🚜 Gestão de Máquinas")
        with st.form("c_veic", clear_on_submit=True):
            nome = st.text_input("Nome da Máquina")
            detalhes = st.text_area("Detalhes")
            if st.form_submit_button("Salvar Veículo"):
                conn.cursor().execute("INSERT INTO veiculos (nome, detalhes) VALUES (?, ?)", (nome.strip(), detalhes.strip()))
                conn.commit(); st.success("✅ Máquina registrada!")

    elif sub_menu == "Relatório de Estoque (Exportar)":
        st.subheader("📑 Inventário Setorial")
        setor_rel = st.selectbox("Selecione o Setor", lista_categorias_dinamica)
        df_estoque = pd.read_sql("SELECT * FROM estoque WHERE categoria = ?", conn, params=(setor_rel,))
        st.dataframe(df_estoque, use_container_width=True)
        if not df_estoque.empty: st.download_button("📥 Exportar Relatório", gerar_relatorio_marcado(df_estoque, f"Estoque - {setor_rel}"), "estoque.csv", "text/csv")

    elif sub_menu == "Relatório de Movimentação (Exportar)":
        st.subheader("📊 Auditoria de Movimentações")
        df_mov = pd.read_sql("SELECT * FROM movimentacoes ORDER BY id DESC", conn)
        st.dataframe(df_mov, use_container_width=True)
        if not df_mov.empty: st.download_button("📥 Exportar Relatório", gerar_relatorio_marcado(df_mov, "Auditoria Geral"), "movimentacoes.csv", "text/csv")

    elif sub_menu == "Gestão de Categorias do Sistema":
        st.subheader("🏷️ Gestão de Categorias")
        nova_categoria = st.text_input("Nova Categoria")
        if st.button("➕ Adicionar"):
            conn.cursor().execute("INSERT INTO categorias (nome) VALUES (?)", (nova_categoria.strip(),))
            conn.commit(); st.rerun()
        for cat in lista_categorias_dinamica:
            st.write(f"• {cat}")

    elif sub_menu == "Controle de Usuários":
        st.subheader("👥 Controle de Acessos")
        
        st.markdown("### 📋 Usuários Cadastrados")
        df_usuarios = pd.read_sql("SELECT usuario, nivel FROM usuarios ORDER BY nivel, usuario", conn)
        if not df_usuarios.empty:
            st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum usuário cadastrado.")
        
        st.markdown("---")
        st.markdown("### ➕ Adicionar/Editar Usuário")
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        nivel = st.selectbox("Nível de Acesso", ["Usuário", "Admin"])
        if st.button("Salvar Operador"):
            if u.strip() and p.strip():
                conn.cursor().execute("INSERT OR REPLACE INTO usuarios VALUES (?,?,?)", (u.strip(), p.strip(), nivel))
                conn.commit()
                st.success(f"✅ Usuário '{u}' salvo com sucesso!")
                st.rerun()
            else:
                st.error("❌ Preencha usuário e senha!")