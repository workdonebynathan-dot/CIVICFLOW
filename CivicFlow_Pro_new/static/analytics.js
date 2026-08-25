x  document.addEventListener("DOMContentLoaded", function() {
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error("Chart.js is not loaded.");
        return;
    }

    // Function to create a standardized chart
    function renderChart(canvasId, type, labels, data, colors, title) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return; // Skip if canvas doesn't exist

        new Chart(ctx.getContext('2d'), {
            type: type,
            data: {
                labels: labels,
                datasets: [{
                    label: title,
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' },
                    title: { display: true, text: title }
                }
            }
        });
    }

    // Colors for the charts
    const statusColors = ['#ffc107', '#17a2b8', '#28a745']; // Yellow, Blue, Green
    const urgencyColors = ['#28a745', '#ffc107', '#dc3545']; // Green, Yellow, Red
    const deptColors = ['#007bff', '#6610f2', '#6f42c1', '#e83e8c', '#fd7e14'];

    // RENDER STATUS CHART (Doughnut)
    // window.statusData is defined in the HTML script tag
    if (window.statusData) {
        renderChart(
            'statusChart', 
            'doughnut', 
            window.statusData.labels, 
            window.statusData.values, 
            statusColors, 
            'Complaints by Status'
        );
    }

    // RENDER URGENCY CHART (Pie)
    if (window.urgencyData) {
        renderChart(
            'urgencyChart', 
            'pie', 
            window.urgencyData.labels, 
            window.urgencyData.values, 
            urgencyColors, 
            'Complaints by Urgency'
        );
    }

    // RENDER DEPARTMENT CHART (Bar)
    if (window.departmentData) {
        renderChart(
            'departmentChart', 
            'bar', 
            window.departmentData.labels, 
            window.departmentData.values, 
            deptColors, 
            'Complaints by Department'
        );
    }
});