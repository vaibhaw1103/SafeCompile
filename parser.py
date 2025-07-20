# parser.py
from parse_tree_node import ParseTreeNode
import ply.yacc as yacc
from lexer import tokens
from ast_nodes import *

# Precedence rules (optional; adjust based on your language)
precedence = (
    ('left', 'PLUS', 'MINUS'),
    ('left', 'MULT', 'DIV'),
    ('nonassoc', 'LT', 'GT', 'LE', 'GE', 'EQ', 'NEQ'),
)

def p_program(p):
    '''program : statement_list'''
    p[0] = ProgramNode(p[1])

def p_statement_list(p):
    '''statement_list : statement_list statement
                      | statement'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_statement(p):
    '''statement : declaration
                 | assignment
                 | if_statement
                 | while_statement
                 | function_declaration
                 | return_statement'''
    p[0] = p[1]

def p_declaration(p):
    '''declaration : TYPE ID SEMICOLON
                   | TYPE ID ASSIGN expression SEMICOLON'''
    if len(p) == 4:
        p[0] = VariableDeclNode(p[2], p[1], None, p.lineno(2))
    else:
        p[0] = VariableDeclNode(p[2], p[1], p[4], p.lineno(2))

def p_assignment(p):
    '''assignment : ID ASSIGN expression SEMICOLON'''
    var = IdentifierNode(p[1], p.lineno(1))
    p[0] = ASTNode('Assignment', [var, p[3]], line=p.lineno(1))

def p_expression_binop(p):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression MULT expression
                  | expression DIV expression
                  | expression LT expression
                  | expression GT expression
                  | expression LE expression
                  | expression GE expression
                  | expression EQ expression
                  | expression NEQ expression'''
    p[0] = BinaryOpNode(p[1], p[2], p[3], line=p.lineno(2))

def p_expression_group(p):
    '''expression : LPAREN expression RPAREN'''
    p[0] = p[2]

def p_expression_number(p):
    '''expression : NUMBER'''
    p[0] = LiteralNode(p[1], line=p.lineno(1))

def p_expression_identifier(p):
    '''expression : ID'''
    p[0] = IdentifierNode(p[1], line=p.lineno(1))

def p_if_statement(p):
    '''if_statement : IF LPAREN expression RPAREN LBRACE statement_list RBRACE
                    | IF LPAREN expression RPAREN LBRACE statement_list RBRACE ELSE LBRACE statement_list RBRACE'''
    if len(p) == 8:
        p[0] = IfStmtNode(p[3], ASTNode('Block', p[6]), None, line=p.lineno(1))
    else:
        p[0] = IfStmtNode(p[3], ASTNode('Block', p[6]), ASTNode('Block', p[10]), line=p.lineno(1))

def p_while_statement(p):
    '''while_statement : WHILE LPAREN expression RPAREN LBRACE statement_list RBRACE'''
    p[0] = WhileStmtNode(p[3], ASTNode('Block', p[6]), line=p.lineno(1))

def p_function_declaration(p):
    '''function_declaration : TYPE ID LPAREN param_list RPAREN LBRACE statement_list RBRACE'''
    p[0] = FunctionDeclNode(p[2], p[4], ASTNode('Block', p[7]), line=p.lineno(2))

def p_param_list(p):
    '''param_list : param_list COMMA param
                  | param
                  | empty'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    elif p[1] is None:
        p[0] = []
    else:
        p[0] = [p[1]]

def p_param(p):
    '''param : TYPE ID'''
    p[0] = VariableDeclNode(p[2], p[1], None, line=p.lineno(2))

def p_return_statement(p):
    '''return_statement : RETURN expression SEMICOLON'''
    p[0] = ASTNode('Return', [p[2]], line=p.lineno(1))

def p_empty(p):
    '''empty :'''
    p[0] = None

def p_error(p):
    if p:
        print(f"Syntax error at token '{p.value}' on line {p.lineno}")
    else:
        print("Syntax error at EOF")

parser = yacc.yacc()
