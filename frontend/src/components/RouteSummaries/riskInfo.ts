/** Definitions shown behind the information icons on each route card. */
export const RISK_INFO = {
  NO_TRAVEL:
    'No Travel is the highest risk level. A checkpoint is No Travel when wind reaches 55 mph, rain exceeds 1.00 in/hr, snow exceeds 3.0 in/hr, or wind is 45 to 54 mph with a load over 30,000 lb. This figure is the route miles forecast at No Travel for the hour the truck drives them. The route with the fewest No Travel miles ranks first.',
  SEVERE:
    'A checkpoint is Severe when its worst condition is wind of 45 to 54 mph with a load of 30,000 lb or less, wind of 35 to 44 mph with a load over 40,000 lb, rain of 0.50 to 1.00 in/hr, or snow of 2.0 to 3.0 in/hr. This figure is the route miles forecast at Severe for the hour the truck drives them. When No Travel miles tie, the route with the fewest Severe miles ranks first.',
  HIGH: 'A checkpoint is High when its worst condition is wind of 35 to 44 mph with a load of 40,000 lb or less, rain of 0.25 to under 0.50 in/hr, or snow of 1.0 to under 2.0 in/hr. This figure is the route miles forecast at High for the hour the truck drives them. When No Travel and Severe miles tie, the route with the fewest High miles ranks first.',
  AVERAGE:
    'Each checkpoint scores 0 for Low, 1 for Moderate, 2 for High, 3 for Severe and 4 for No Travel. This figure averages those scores, weighted by the miles each checkpoint covers. When No Travel, Severe and High miles tie, the route with the lowest average ranks first.',
} as const;
