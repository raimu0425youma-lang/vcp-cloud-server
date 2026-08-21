let totalSaved = 0.00;

document.getElementById("sendBtn").addEventListener("click", async () => {
  const input = document.getElementById("promptInput").value.trim();
  const resDiv = document.getElementById("result");
  const badge = document.getElementById("routeBadge");
  const savingsVal = document.getElementById("savingsVal");

  if (!input) {
    resDiv.innerText = "⚠️ 質問を入力してください。";
    return;
  }

  resDiv.innerText = "⚡ プロンプト解析中... 最適なモデルへルーティング中...";
  badge.style.display = "none";

  try {
    const res = await fetch("http://localhost:8000/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: [{ role: "user", content: input }]
      })
    });
    const data = await res.json();

    // 応答の表示
    const reply = data.choices?.[0]?.message?.content || JSON.stringify(data, null, 2);
    resDiv.innerText = reply;

    // ルーティング結果の更新（デモ用表示）
    badge.style.display = "inline-block";
    badge.innerText = "🔀 障害自動回避: Anthropic Claude にリレー完了";

    // 節約額の可視化 (ダミー計算)
    totalSaved += 0.02;
    savingsVal.innerText = `$${totalSaved.toFixed(2)}`;

  } catch (err) {
    resDiv.innerText = "❌ 接続失敗: AEGサーバー(localhost:8000)が起動しているか確認してください。";
  }
});
