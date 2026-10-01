// ===== 1. Загрузка данных =====
async function loadSiteData() {
    try {
        const response = await fetch('site.json');
        if (!response.ok) throw new Error('Не удалось загрузить site.json');
        return await response.json();
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
        return null;
    }
}

// ===== 2. Заполнение текстов =====
function fillText(data) {
    // Название салона (шапка + подвал)
    document.querySelectorAll('#salon-name, #footer-name').forEach(el => {
        el.textContent = data.salon_name;
    });

    // Hero
    document.getElementById('hero-title').textContent = data.hero_title;
    document.getElementById('hero-subtitle').textContent = data.hero_subtitle;

    // Контакты
    const phoneEl = document.getElementById('contact-phone');
    phoneEl.textContent = data.phone;
    phoneEl.href = 'tel:' + data.phone.replace(/[^\d+]/g, '');

    document.getElementById('contact-address').textContent = data.address;

    // Год в подвале
    document.getElementById('footer-year').textContent = new Date().getFullYear();

    // Title вкладки браузера
    document.title = data.salon_name + ' — онлайн-запись';
}

// ===== 3. Рендер услуг =====
function renderServices(services) {
    const container = document.getElementById('services-list');
    container.innerHTML = '';

    if (!services || services.length === 0) {
        container.innerHTML = '<p class="loading">Услуги пока не добавлены</p>';
        return;
    }

    services.forEach(service => {
        const card = document.createElement('div');
        card.className = 'service-card';
        card.innerHTML = `
            <div class="service-card__name">${service.name}</div>
            <div class="service-card__meta">
                <div class="service-card__price">${service.price.toLocaleString('ru-RU')} ₽</div>
                <div class="service-card__duration">⏱ ${service.duration} мин</div>
            </div>
        `;
        container.appendChild(card);
    });
}

// ===== 4. Рендер соцсетей =====
function renderSocials(socials) {
    const container = document.getElementById('socials-list');
    container.innerHTML = '';

    if (!socials || socials.length === 0) {
        container.parentElement.style.display = 'none';
        return;
    }

    socials.forEach(social => {
        const link = document.createElement('a');
        link.className = 'social-btn';
        link.href = social.url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.innerHTML = `<span>${social.icon}</span><span>${social.name}</span>`;
        container.appendChild(link);
    });
}

// ===== 5. Настройка кнопок =====
function setupButtons(data) {
    // Все кнопки "Записаться" ведут на бота
    const bookingLinks = document.querySelectorAll('a[href="#booking"], #booking-btn');

    bookingLinks.forEach(link => {
        if (link.id === 'booking-btn') {
            // Кнопка в CTA-блоке — прямая ссылка на бота
            link.href = data.telegram_bot;
        } else {
            // Кнопки в шапке и hero — ведут к секции CTA
            link.href = '#booking';
        }
    });
}

// ===== 6. Запуск =====
async function init() {
    const data = await loadSiteData();
    if (!data) return;

    fillText(data);
    renderServices(data.services);
    renderSocials(data.socials);
    setupButtons(data);
}

init();