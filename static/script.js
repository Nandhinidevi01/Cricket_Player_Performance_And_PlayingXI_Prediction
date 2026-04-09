document.getElementById("predictBtn").addEventListener("click", () => {

    const squad = document.getElementById("players").value;
    const venue = document.getElementById("venue").value;
    const opponent = document.getElementById("opponent").value;
    const gender = document.getElementById("gender").value;
    const pitch = document.getElementById("pitch").value;
    const captain = document.getElementById("captain").value;
    const viceCaptain = document.getElementById("vice_captain").value;

    const output = document.getElementById("output");
    output.innerHTML = "⏳ Predicting...";

    fetch("/predict", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            players: squad,
            venue: venue,
            opponent: opponent,
            gender: gender,
            pitch: pitch,
            captain: captain,
            vice_captain: viceCaptain
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.error) {
            output.innerHTML = data.error;
            return;
        }

        let html = `<div class="grid">`;

        data.players.forEach(p => {
            html += `
                <div class="card">
                    <h3>${p.name}</h3>
                    <p>${p.role}</p>
                    <p>Runs: ${p.runs}</p>
                    ${p.role !== "BATSMAN" && p.role !== "WICKETKEEPER" ? `<p>Wickets: ${p.wickets}</p>` : ""}
                    <p>Confidence: ${p.confidence}%</p>
                    ${p.captain ? "<span class='badge captain'>C</span>" : ""}
                    ${p.vice_captain ? "<span class='badge vc'>VC</span>" : ""}
                </div>
            `;
        });

        html += `</div>`;
        output.innerHTML = html;

    })
    .catch(() => {
        output.innerHTML = "Something went wrong";
    });
});