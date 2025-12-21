import React, { createContext, useContext, useState, useCallback } from 'react';

const RecommendationsContext = createContext();

export const RecommendationsProvider = ({ children }) => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const invalidateRecommendations = useCallback((reason = 'unknown') => {
    console.log(`🔄 Invalidating recommendations: ${reason}`);
    setRefreshTrigger((prev) => {
      const newValue = prev + 1;
      console.log(`   📈 refreshTrigger: ${prev} → ${newValue}`); // ← DODANE
      return newValue;
    });
  }, []);

  // ✅ DODAJ - Zobacz kiedy Context się renderuje
  console.log('🎯 RecommendationsContext render, refreshTrigger =', refreshTrigger);

  return (
    <RecommendationsContext.Provider
      value={{
        refreshTrigger,
        invalidateRecommendations,
      }}
    >
      {children}
    </RecommendationsContext.Provider>
  );
};

export const useRecommendations = () => {
  const context = useContext(RecommendationsContext);
  if (!context) {
    throw new Error('useRecommendations must be used within RecommendationsProvider');
  }
  return context;
};
