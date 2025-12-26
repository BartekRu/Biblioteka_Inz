import React, { createContext, useContext, useState, useCallback } from 'react';

const RecommendationsContext = createContext();

export const RecommendationsProvider = ({ children }) => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const invalidateRecommendations = useCallback((reason = 'unknown') => {
    setRefreshTrigger((prev) => {
      const newValue = prev + 1;
      return newValue;
    });
  }, []);

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
