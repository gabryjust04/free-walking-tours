(function () {
    const stopsList = document.getElementById("stops-list");
    const stopTemplate = document.getElementById("stop-template");
    const addStopButton = document.getElementById("add-stop-btn");

    if (!stopsList || !stopTemplate || !addStopButton) {
        return;
    }

    function refreshStopLabels() {
        stopsList.querySelectorAll(".stop-row").forEach((row, index) => {
            row.querySelector(".stop-order-label").textContent = `Stop ${index + 1}`;
        });
    }

    function attachRemoveHandler(row) {
        row.querySelector(".remove-stop-btn").addEventListener("click", () => {
            row.remove();
            refreshStopLabels();
        });
    }

    function addStop() {
        const clone = stopTemplate.content.cloneNode(true);
        const row = clone.querySelector(".stop-row");

        attachRemoveHandler(row);
        stopsList.appendChild(row);
        refreshStopLabels();
    }

    addStopButton.addEventListener("click", addStop);
    stopsList.querySelectorAll(".stop-row").forEach(attachRemoveHandler);
    refreshStopLabels();
})();
