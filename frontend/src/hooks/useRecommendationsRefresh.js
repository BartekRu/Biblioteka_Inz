import { useState, useCallback } from 'react';

export const useRecommendationsRefresh = () => {
  const [refreshKey, setRefreshKey] = useState(0);

  const triggerRefresh = useCallback(() => {
    setRefreshKey((prev) => prev + 1);
    console.log('🔄 Triggering recommendations refresh');
  }, []);

  return { refreshKey, triggerRefresh };
};
