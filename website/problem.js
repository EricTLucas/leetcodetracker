const db = firebase.firestore();

function getSlug() {
    const params = new URLSearchParams(window.location.search);
    return params.get("slug");
}

async function loadProblem() {
    const slug = getSlug();
    if (!slug) {
        document.getElementById("title").textContent = "No problem slug provided.";
        return;
    }

    const docRef = db
        .collection("leetcode")
        .doc("problems")
        .collection("items")
        .doc(slug);

    const docSnap = await docRef.get();

    if (!docSnap.exists) {
        document.getElementById("title").textContent = "Problem not found.";
        return;
    }

    const data = docSnap.data();

    // Title
    document.getElementById("title").textContent = data.titleSlug;

    // Meta info
    const meta = document.getElementById("meta");
    meta.innerHTML = `
        <div>Submitted: ${new Date(data.timestamp * 1000).toLocaleString()}</div>
        <div>Status: ${data.statusDisplay}</div>
        <div>Language: ${data.lang}</div>
    `;

    // Code
    document.getElementById("code").textContent = data.code || "No code available.";

    // Stats
    const stats = document.getElementById("stats");
    stats.innerHTML = `
        <div>Runtime: ${data.runtime} (${data.runtime_percentile} percentile)</div>
        <div>Memory: ${data.memory} (${data.memory_percentile} percentile)</div>
    `;
}

window.onload = loadProblem;
