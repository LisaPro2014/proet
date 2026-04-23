document.addEventListener('DOMContentLoaded', function () { // тут что то конфликтует, я плка не поняла что
    const searchInput = document.getElementById('gameSearchInput');

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const searchQuery = this.value.toLowerCase();
            const gameCards = document.querySelectorAll('.game-card');

            gameCards.forEach(card => {
                const title = card.querySelector('.game-title').textContent.toLowerCase();

                if (title.includes(searchQuery)) {
                    card.style.display = 'block';
                    setTimeout(() => {
                        card.style.opacity = '1';
                        card.style.transform = 'scale(1)';
                    }, 10);
                } else {
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.95)';
                    setTimeout(() => {
                        if (card.style.opacity === '0') {
                            card.style.display = 'none';
                        }
                    }, 300);
                }
            });
        });
    }

});