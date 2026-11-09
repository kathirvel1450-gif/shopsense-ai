import { useCallback, useEffect, useState } from 'react';

export function useApiData(loader, dependencies = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const reload = useCallback(async () => {
    setLoading(true); setError('');
    try { setData(await loader()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to load data'); }
    finally { setLoading(false); }
  // Loader identity is intentionally controlled by the supplied dependency list.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);
  useEffect(() => { reload(); }, [reload]);
  return { data, loading, error, reload, setData };
}
