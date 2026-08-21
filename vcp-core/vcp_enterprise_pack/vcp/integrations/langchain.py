class VCPLangChainMiddleware:
    """
    LangChain や OpenAI Agent の Tool Call 手前に挟み込む自動判定インターセプター
    """
    def __init__(self, policy_engine):
        self.engine = policy_engine

    def wrap_tool(self, tool_func, action: str, resource: str):
        def guarded_tool(*args, **kwargs):
            amount = kwargs.get("amount", 0)
            authorized, reason = self.engine.authorize(action, resource, amount)
            if not authorized:
                print(f"  └─ ⛔ [VCP Middleware Block] {reason}")
                return {"error": True, "message": f"VCP Security Intercept: {reason}"}
            
            print(f"  └─ ⚡ [VCP Middleware Pass] Action '{action}' 承認完了。実行します。")
            return tool_func(*args, **kwargs)
        return guarded_tool
