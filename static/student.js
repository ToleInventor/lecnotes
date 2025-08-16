document.addEventListener('DOMContentLoaded', () => {
    // Year filter
    const yearFilter = document.getElementById('yearFilter');
    yearFilter.value = 'all';
    
    yearFilter.addEventListener('change', () => {
        const selectedYear = yearFilter.value;
        const lectureRows = document.querySelectorAll('.lecture-row');
        
        lectureRows.forEach(row => {
            if (selectedYear === 'all' || row.dataset.year === selectedYear) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });

    // Lecture modal
    const viewButtons = document.querySelectorAll('.view-lecture');
    const lectureModal = new bootstrap.Modal(document.getElementById('lectureModal'));
    
    viewButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const lectureId = button.dataset.id;
            
            fetch(`/get_lecture/${lectureId}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('lectureTitle').textContent = data.title;
                    document.getElementById('lectureContent').innerHTML = 
                        `<p><strong>Course:</strong> ${data.course}</p>
                         <p><strong>Lecturer:</strong> ${data.author}</p>
                         <p><strong>Date:</strong> ${new Date(data.timestamp).toLocaleString()}</p>
                         <hr>
                         <div>${data.content.replace(/\n/g, '<br>')}</div>`;
                    lectureModal.show();
                });
        });
    });
});