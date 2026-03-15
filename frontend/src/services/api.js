const API = 'http://localhost:8000';

async function parse(res) {
  const payload = await res.json();
  if (!res.ok) {
    throw new Error(payload.detail || 'Request failed');
  }
  return payload;
}

export async function getRankings() {
  return fetch(`${API}/rankings`).then(parse);
}

export async function syncData() {
  return fetch(`${API}/sync`, { method: 'POST' }).then(parse);
}

export async function searchStocks(q) {
  return fetch(`${API}/search?q=${encodeURIComponent(q)}`).then(parse);
}

export async function getStock(ticker) {
  return fetch(`${API}/stock/${encodeURIComponent(ticker)}`).then(parse);
}

export async function evaluateLive(query) {
  return fetch(`${API}/evaluate-live?query=${encodeURIComponent(query)}`).then(parse);
}

export async function getWishlist() {
  return fetch(`${API}/wishlist`).then(parse);
}

export async function saveWishlistItem(item) {
  return fetch(`${API}/wishlist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(item),
  }).then(parse);
}

export async function deleteWishlistItem(ticker) {
  return fetch(`${API}/wishlist/${encodeURIComponent(ticker)}`, { method: 'DELETE' }).then(parse);
}

export async function recalc(weights) {
  return fetch(`${API}/recalculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(weights),
  }).then(parse);
}
