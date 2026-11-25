(() => {
  const menuButton = document.querySelector('.mobile-menu');
  const nav = document.querySelector('.main-nav');
  if (menuButton && nav) {
    menuButton.addEventListener('click', () => {
      const open = nav.classList.toggle('nav-open');
      menuButton.setAttribute('aria-expanded', String(open));
    });
  }

  document.querySelectorAll('.flash button').forEach((button) => {
    button.addEventListener('click', () => button.closest('.flash')?.remove());
  });

  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!window.confirm(form.dataset.confirm || 'Continue?')) event.preventDefault();
    });
  });

  const travelerSelect = document.querySelector('#travelers');
  const priceText = document.querySelector('[data-price-per-person]');
  const totalText = document.querySelector('[data-live-total]');
  if (travelerSelect && priceText && totalText) {
    const price = Number(priceText.dataset.pricePerPerson || 0);
    const updateTotal = () => {
      const count = Number(travelerSelect.value || 1);
      totalText.textContent = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price * count);
    };
    travelerSelect.addEventListener('change', updateTotal);
    updateTotal();
  }
})();
