// static/js/custom.js
$(document).ready(function() {
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
    
    // Initialize all select2 dropdowns
    $('.select2').select2({
        theme: 'bootstrap-5'
    });
    
    // Add active class to current nav item
    var currentUrl = window.location.pathname;
    $('.sidebar .nav-link').each(function() {
        if ($(this).attr('href') === currentUrl) {
            $(this).addClass('active');
        }
    });
});

// Global Functions
window.confirmDelete = function(url, message) {
    Swal.fire({
        title: 'Are you sure?',
        text: message || 'This action cannot be undone!',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!'
    }).then((result) => {
        if (result.isConfirmed) {
            window.location.href = url;
        }
    });
    return false;
};

window.formatCurrency = function(amount) {
    return '$' + parseFloat(amount).toFixed(2);
};

window.showLoading = function() {
    Swal.fire({
        title: 'Loading...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
};

window.hideLoading = function() {
    Swal.close();
};

window.showSuccess = function(message) {
    Swal.fire({
        icon: 'success',
        title: 'Success!',
        text: message,
        timer: 3000,
        showConfirmButton: false
    });
};

window.showError = function(message) {
    Swal.fire({
        icon: 'error',
        title: 'Error!',
        text: message,
        confirmButtonColor: '#d33'
    });
};

window.showWarning = function(message) {
    Swal.fire({
        icon: 'warning',
        title: 'Warning!',
        text: message,
        confirmButtonColor: '#f39c12'
    });
};

window.showInfo = function(message) {
    Swal.fire({
        icon: 'info',
        title: 'Information',
        text: message,
        confirmButtonColor: '#3498db'
    });
};

// Function to print bill
window.printBill = function() {
    window.print();
};

// Function to update order status via AJAX
window.updateOrderStatus = function(orderId, status) {
    $.ajax({
        url: `/orders/orders/${orderId}/update-status/`,
        method: 'POST',
        data: {
            status: status,
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(response) {
            if (response.success) {
                showSuccess('Order status updated successfully');
                location.reload();
            } else {
                showError('Failed to update status');
            }
        },
        error: function() {
            showError('An error occurred');
        }
    });
};

// Function to send to kitchen
window.sendToKitchen = function(orderItemId) {
    $.ajax({
        url: `/orders/kitchen-print/${orderItemId}/`,
        method: 'POST',
        data: {
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(response) {
            if (response.success) {
                showSuccess('Order sent to kitchen');
                location.reload();
            } else {
                showError('Failed to send to kitchen');
            }
        },
        error: function() {
            showError('An error occurred');
        }
    });
};

// Function to load chart data
window.loadChart = function(chartId, type, labels, data) {
    const ctx = document.getElementById(chartId).getContext('2d');
    return new Chart(ctx, {
        type: type,
        data: {
            labels: labels,
            datasets: [{
                label: 'Data',
                data: data,
                backgroundColor: [
                    'rgba(54, 162, 235, 0.5)',
                    'rgba(255, 99, 132, 0.5)',
                    'rgba(75, 192, 192, 0.5)',
                    'rgba(255, 206, 86, 0.5)',
                    'rgba(153, 102, 255, 0.5)'
                ],
                borderColor: [
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(153, 102, 255, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
};