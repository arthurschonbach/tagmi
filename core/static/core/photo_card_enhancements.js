// photo_card_enhancements.js

/**
 * Initializes the tag search functionality for a single photo card.
 * @param {HTMLElement} cardElement - The main <div id="photo-card-XYZ"> element.
 */
function initializeTagSearchForCard(cardElement) {
    if (!cardElement || !cardElement.id || !cardElement.id.startsWith('photo-card-')) return;
    if (cardElement.id.startsWith('photo-card-body-')) return;

    const idParts = cardElement.id.split('-');
    const photoId = idParts[idParts.length - 1];
    if (!photoId || isNaN(parseInt(photoId))) return;

    const searchInputSelector = `#tag-search-${photoId}`;
    const tagListContainerSelector = `#tag-list-${photoId}`;
    const searchInput = cardElement.querySelector(searchInputSelector);
    const tagListContainer = cardElement.querySelector(tagListContainerSelector);
    if (!searchInput || !tagListContainer) return;

    const tagItems = tagListContainer.querySelectorAll('.tag-item');

    // Define the filter handler
    const filterTagsHandler = function(event) {
        const searchTerm = event.target.value.toLowerCase().trim();
        tagItems.forEach(item => {
            const label = item.querySelector('.tag-label');
            if (label) {
                const labelText = label.textContent.toLowerCase();
                item.style.display = labelText.includes(searchTerm) ? 'flex' : 'none';
            }
        });
    };

    // Remove previous handler if any
    if (searchInput._filterTagsHandler) {
        searchInput.removeEventListener('input', searchInput._filterTagsHandler);
    }

    // Assign and bind the handler
    searchInput._filterTagsHandler = filterTagsHandler;
    searchInput.addEventListener('input', filterTagsHandler);
}

/**
 * Initializes tag search for all photo cards within a given root element.
 * @param {HTMLElement} [rootElement=document] - The element to search within for photo cards.
 */
function setupPhotoCards(rootElement = document) {
    const photoCards = rootElement.querySelectorAll('div[id^="photo-card-"]:not([id*="-body-"])');
    photoCards.forEach(card => {
        initializeTagSearchForCard(card);
    });
}

// Initialize for all cards on initial page load
document.addEventListener('DOMContentLoaded', () => {
    setupPhotoCards(document);
});

// Re-initialize after HTMX swaps
document.body.addEventListener('htmx:afterSwap', function(event) {
    const oldElement = event.detail.target;
    if (!oldElement || !oldElement.id) return;

    setTimeout(() => {
        const newElement = document.querySelector(`#${oldElement.id}`);
        if (newElement && newElement.id.startsWith('photo-card-') && !newElement.id.includes('-body-')) {
            initializeTagSearchForCard(newElement);
        } else {
            setupPhotoCards(document);
        }
    }, 0);
});
