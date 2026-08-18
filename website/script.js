const db = firebase.firestore();

function makeSnippet(code) {
    if (!code) return "";
    return code.split("\n").slice(0, 3).join("\n");
}

async function loadStats() {
    const docSnap = await db.collection("leetcode").doc("stats").get();
    const stats = docSnap.data();

    document.getElementById("total-unique").textContent = stats.total_unique_solved;
    document.getElementById("solved-week").textContent = stats.solved_week;
}

async function loadRecent() {
    const container = document.getElementById("problems");
    container.innerHTML = "Loading...";

    const snapshot = await db
        .collection("leetcode")
        .doc("problems")
        .collection("items")
        .orderBy("timestamp", "desc")
        .limit(20)
        .get();

    container.innerHTML = "";

    snapshot.forEach(doc => {
        const sub = doc.data();
        const snippet = makeSnippet(sub.code);

        const div = document.createElement("div");
        div.className = "problem-item";
        div.onclick = () => openProblem(sub.title_slug);

        div.innerHTML = `
            <div class="problem-title">
                ${sub.title}
            </div>

            <div class="circle-container">
                <div class="circle" style="--pct:${parseFloat(sub.runtime_percentile)};">
                    <div class="circle-inner">${sub.runtime}</div>
                </div>

                <div class="circle" style="--pct:${parseFloat(sub.memory_percentile)};">
                    <div class="circle-inner">${sub.memory}</div>
                </div>
            </div>

            <pre class="preview-code">${snippet}</pre>

            <div class="problem-meta">
                Submitted: ${new Date(sub.timestamp * 1000).toLocaleDateString()}
            </div>
        `;

        
        container.appendChild(div);
    });
}

function openProblem(slug) {
    window.location.href = `problem.html?slug=${slug}`;
}

window.onload = async () => {
    await loadStats();
    await loadRecent();
};
