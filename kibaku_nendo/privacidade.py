"""
Privacidade: o que identifica uma pessoa (CPF, e-mail, telefone... e o nome numa tabela de pessoas).
O esboço deixa essas colunas de fora e o validar avisa quando uma delas entra no modelo sem uso (LGPD: só o
necessário).
"""

from tecnicas.luneta.descoberta import tokens

PESSOAIS = {'cpf', 'rg', 'cnh', 'pis', 'email', 'telefone', 'celular', 'nascimento', 'endereco', 'logradouro', 'cep',
            'mae', 'pai', 'sexo', 'genero', 'raca', 'religiao'}
TABELAS_DE_PESSOA = {'funcionario', 'colaborador', 'empregado', 'pessoa', 'cliente', 'paciente', 'aluno', 'candidato',
                     'fornecedor_pf', 'usuario', 'chapa'}

def pessoal(t, coluna):
    """Coluna que identifica uma pessoa (CPF, e-mail... e o nome numa tabela de pessoas)."""
    toks = set(tokens(coluna['coluna']))
    if toks & PESSOAIS:
        return True
    de_pessoa = bool(set(tokens(t['nome'])) & TABELAS_DE_PESSOA)
    return de_pessoa and bool(toks & {'nome', 'nm', 'apelido'})
