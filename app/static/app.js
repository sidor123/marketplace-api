'use strict';
const $ = (selector) => document.querySelector(selector);
const state = { auth: null, page: 0, size: 9, total: 0, editing: null, deleting: null, register: false, loadId: 0 };
const statuses = { ACTIVE: 'В продаже', INACTIVE: 'Неактивен', ARCHIVED: 'В архиве' };
const money = (value) => new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format(value);
function notice(message, error = false) {
  $('#notice').textContent = message;
  $('#notice').dataset.error = error;
  $('#notice').hidden = false;
}
async function api(path, options = {}, retry = true) {
  const headers = { ...options.headers };
  if (options.body) headers['Content-Type'] = 'application/json';
  if (state.auth) headers.Authorization = `Bearer ${state.auth.access_token}`;
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401 && state.auth && retry) {
    const refresh = await fetch('/auth/refresh', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: state.auth.refresh_token }) });
    if (refresh.ok) {
      Object.assign(state.auth, await refresh.json());
      return api(path, options, false);
    }
    state.auth = null;
    updateAccount();
    throw new Error('Сессия истекла. Войдите снова.');
  }
  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) {
    const fields = data.details?.fields;
    throw new Error(fields ? Object.entries(fields).map(([field, value]) => `${field}: ${value}`).join('\n') : data.message || 'Не удалось выполнить запрос');
  }
  return data;
}
function updateAccount() {
  const user = state.auth?.user;
  $('#account-button').textContent = user ? 'Выйти' : 'Войти';
  $('#account-label').textContent = user ? `${user.email} · ${user.role === 'SELLER' ? 'Продавец' : user.role === 'ADMIN' ? 'Администратор' : 'Покупатель'}` : 'Просмотр доступен без входа';
  $('#create-button').hidden = !user || !['SELLER', 'ADMIN'].includes(user.role);
}
function element(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}
function action(label, handler) {
  const button = element('button', 'secondary', label);
  button.type = 'button';
  button.addEventListener('click', () => Promise.resolve(handler()).catch((error) => notice(error.message, true)));
  return button;
}
function card(product) {
  const node = element('article', 'card', '');
  const top = element('div', 'card-top', '');
  top.dataset.status = product.status;
  top.append(element('span', '', product.category), element('span', '', statuses[product.status]));
  const body = element('div', 'card-body', '');
  body.append(element('h3', '', product.name), element('p', '', product.description || 'Описание пока не добавлено.'));
  const price = element('div', 'price-row', '');
  price.append(element('span', 'price', money(product.price)), element('span', 'stock', `${product.stock} шт.`));
  const actions = element('div', 'actions', '');
  actions.append(action('Подробнее', async () => {
    const detail = await api(`/products/${product.id}`);
    $('#detail-title').textContent = detail.name;
    $('#detail-body').textContent = `${detail.description || 'Без описания'}\n\n${money(detail.price)} · ${detail.stock} шт.\n${detail.category} · ${statuses[detail.status]}\n\nОбновлено: ${new Date(detail.updated_at).toLocaleString('ru-RU')}\nID: ${detail.id}`;
    $('#detail-dialog').showModal();
  }));
  const user = state.auth?.user;
  if (user && (user.role === 'ADMIN' || (user.role === 'SELLER' && product.seller_id === user.id))) {
    actions.append(action('Изменить', () => editProduct(product)));
    if (product.status !== 'ARCHIVED') actions.append(action('В архив', () => {
      state.deleting = product.id;
      $('#delete-form .form-error').textContent = '';
      $('#delete-dialog').showModal();
    }));
  }
  body.append(price, actions);
  node.append(top, body);
  return node;
}
async function loadProducts() {
  const loadId = ++state.loadId;
  const query = new URLSearchParams(new FormData($('#filters')));
  query.set('page', state.page);
  query.set('size', state.size);
  $('#products').setAttribute('aria-busy', 'true');
  try {
    const data = await api(`/products?${query}`);
    if (loadId !== state.loadId) return;
    state.total = data.total_elements;
    if (!data.items.length && state.page > 0) { state.page--; return await loadProducts(); }
    $('#total').textContent = state.total;
    $('#products').replaceChildren(...data.items.map(card));
    if (!data.items.length) $('#products').append(element('div', 'empty', 'Здесь пока нет товаров. Добавьте первый товар или измените фильтры.'));
    $('#prev').disabled = state.page === 0;
    $('#next').disabled = (state.page + 1) * state.size >= state.total;
    $('#page-label').textContent = `Страница ${state.page + 1} из ${Math.max(1, Math.ceil(state.total / state.size))}`;
  } catch (error) {
    if (loadId === state.loadId) {
      $('#products').replaceChildren(element('div', 'empty', 'Не удалось загрузить каталог. Повторите запрос кнопкой «Показать».'));
      notice(error.message, true);
    }
  } finally { if (loadId === state.loadId) $('#products').removeAttribute('aria-busy'); }
}
function editProduct(product = null) {
  state.editing = product?.id || null;
  const form = $('#product-form');
  form.reset();
  form.querySelector('.form-error').textContent = '';
  $('#product-title').textContent = product ? 'Редактирование товара' : 'Новый товар';
  if (product) for (const key of ['name', 'description', 'price', 'stock', 'category', 'status']) form.elements[key].value = product[key] ?? '';
  $('#product-dialog').showModal();
}
async function submit(form, operation) {
  const button = form.querySelector('[type=submit]');
  const error = form.querySelector('.form-error');
  error.textContent = '';
  button.disabled = true;
  try { await operation(); } catch (e) { error.textContent = e.message; } finally { button.disabled = false; }
}
$('#account-button').addEventListener('click', () => {
  if (state.auth) { state.auth = null; updateAccount(); loadProducts(); notice('Вы вышли из аккаунта.'); }
  else { $('#auth-form .form-error').textContent = ''; $('#auth-dialog').showModal(); }
});
$('#auth-toggle').addEventListener('click', () => {
  state.register = !state.register;
  $('#role-field').hidden = !state.register;
  $('#auth-title').textContent = state.register ? 'Создать аккаунт' : 'Вход в Маркет';
  $('#auth-submit').textContent = state.register ? 'Зарегистрироваться' : 'Войти';
  $('#auth-toggle').textContent = state.register ? 'Уже есть аккаунт? Войти' : 'Нет аккаунта? Зарегистрироваться';
  $('#auth-form [name=password]').autocomplete = state.register ? 'new-password' : 'current-password';
});
$('#auth-form').addEventListener('submit', (event) => {
  event.preventDefault();
  submit(event.target, async () => {
    const data = Object.fromEntries(new FormData(event.target));
    if (!state.register) delete data.role;
    state.auth = await api(state.register ? '/auth/register' : '/auth/login', { method: 'POST', body: JSON.stringify(data) });
    event.target.reset();
    updateAccount();
    $('#auth-dialog').close();
    notice('Вы вошли в аккаунт.');
    await loadProducts();
  });
});
$('#product-form').addEventListener('submit', (event) => {
  event.preventDefault();
  submit(event.target, async () => {
    const data = Object.fromEntries(new FormData(event.target));
    data.stock = Number(data.stock);
    await api(state.editing ? `/products/${state.editing}` : '/products', { method: state.editing ? 'PUT' : 'POST', body: JSON.stringify(data) });
    $('#product-dialog').close();
    notice('Товар сохранён.');
    await loadProducts();
  });
});
$('#delete-form').addEventListener('submit', (event) => {
  event.preventDefault();
  submit(event.target, async () => {
    await api(`/products/${state.deleting}`, { method: 'DELETE' });
    $('#delete-dialog').close();
    notice('Товар перенесён в архив.');
    await loadProducts();
  });
});
$('#filters').addEventListener('submit', (event) => { event.preventDefault(); state.page = 0; loadProducts(); });
$('#prev').addEventListener('click', () => { state.page--; loadProducts(); });
$('#next').addEventListener('click', () => { state.page++; loadProducts(); });
$('#create-button').addEventListener('click', () => editProduct());
for (const button of document.querySelectorAll('.close')) button.addEventListener('click', () => button.closest('dialog').close());
updateAccount();
loadProducts();
