import ast
import operator

TOOL_SCHEMA = {
    "name": "calculator",
    "description": "安全地计算数学表达式",
    "category": "utility",
    "permission": "none",
    "version": "1.0",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "数学表达式，例如: (12+8)*5"}
        },
        "required": ["expression"]
    }
}

def execute(expression=None, **kwargs):
    if not expression:
        return {"success": False, "error": "表达式不能为空"}
    
    # 安全的 AST 表达式求值
    operators = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.BitXor: operator.xor,
        ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Mod: operator.mod
    }
    def eval_expr(node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            return operators[type(node.op)](eval_expr(node.left), eval_expr(node.right))
        elif isinstance(node, ast.UnaryOp):
            return operators[type(node.op)](eval_expr(node.operand))
        else:
            raise TypeError(node)
            
    try:
        parsed = ast.parse(expression, mode='eval').body
        result = eval_expr(parsed)
        return {"success": True, "data": {"result": result}, "message": "计算成功"}
    except Exception as e:
        return {"success": False, "error": f"非法的表达式或计算失败: {e}"}
