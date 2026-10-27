// Browser copies of research projects. Stores only the portable copy (the object from
// GET /api/research/project, evidence text included). Never stores keys. Every call fails
// soft: when IndexedDB is unavailable (for example a private window) the app keeps working
// without persistence and isAvailable() returns false.
const DB = 'relay-research', STORE = 'projects', FORMAT = 'relay-research/1';
let dbPromise = null;

export function openStore() {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise(resolve => {
    try {
      if (!globalThis.indexedDB) return resolve(null);
      const req = indexedDB.open(DB, 1);
      req.onupgradeneeded = () => {
        if (!req.result.objectStoreNames.contains(STORE)) req.result.createObjectStore(STORE, {keyPath: 'id'});
      };
      req.onsuccess = () => {
        const db = req.result;
        db.onversionchange = () => db.close();
        resolve(db);
      };
      req.onerror = () => resolve(null);
      req.onblocked = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
  return dbPromise;
}

export async function isAvailable() {
  try {
    return !!(await openStore());
  } catch {
    return false;
  }
}

// Runs one request in its own transaction. Throws when the store is unavailable.
async function run(mode, make) {
  const db = await openStore();
  if (!db) throw new Error('no store');
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, mode);
    const req = make(tx.objectStore(STORE));
    let out;
    if (req) req.onsuccess = () => { out = req.result; };
    tx.oncomplete = () => resolve(out);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error('aborted'));
  });
}

// Saves a portable copy: {format:'relay-research/1', project:{...}}. Returns true on success.
export async function saveProject(doc) {
  try {
    if (!doc || doc.format !== FORMAT || !doc.project || typeof doc.project !== 'object') return false;
    const copy = JSON.parse(JSON.stringify(doc));
    delete copy.project.providerKey;
    delete copy.project.tavilyKey;
    const id = String(copy.project.id || '');
    if (!/^[a-f0-9]{16}$/.test(id)) return false;
    const record = {
      id,
      hypothesis: String(copy.project.hypothesis || '').slice(0, 2000),
      savedAt: new Date().toISOString(),
      doc: copy,
    };
    await run('readwrite', st => st.put(record));
    return true;
  } catch {
    return false;
  }
}

// Lists the local copies as small records (no evidence text is returned).
export async function listProjects() {
  try {
    const records = (await run('readonly', st => st.getAll())) || [];
    return records
      .map(r => ({id: r.id, hypothesis: r.hypothesis || '', savedAt: r.savedAt || ''}))
      .sort((a, b) => b.savedAt.localeCompare(a.savedAt));
  } catch {
    return [];
  }
}

// Returns the portable copy {format, project} for an id, or null.
export async function getProject(id) {
  try {
    const record = await run('readonly', st => st.get(String(id)));
    return record?.doc || null;
  } catch {
    return null;
  }
}

export async function deleteProject(id) {
  try {
    await run('readwrite', st => st.delete(String(id)));
    return true;
  } catch {
    return false;
  }
}

// Bytes used by this origin, when the browser reports it. Returns null otherwise.
export async function estimateStorage() {
  try {
    const e = await navigator.storage?.estimate?.();
    return e ? {usage: e.usage || 0, quota: e.quota || 0} : null;
  } catch {
    return null;
  }
}
