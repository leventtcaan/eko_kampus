import React from 'react';
import { Text } from 'react-native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

import HomeScreen from '../screens/HomeScreen';
import BountyScreen from '../screens/BountyScreen';
import DetectiveScreen from '../screens/DetectiveScreen';
import LeaderboardScreen from '../screens/LeaderboardScreen';
import ProfileScreen from '../screens/ProfileScreen';

export type RootTabParamList = {
  Home: undefined;
  Bounty: undefined;
  Detective: undefined;
  Leaderboard: undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<RootTabParamList>();

const icon = (emoji: string) => () => <Text style={{ fontSize: 20 }}>{emoji}</Text>;

export default function AppNavigator() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: false }}>
      <Tab.Screen name="Home" component={HomeScreen} options={{ title: 'Çöp At', tabBarIcon: icon('♻️') }} />
      <Tab.Screen name="Bounty" component={BountyScreen} options={{ title: 'Görevler', tabBarIcon: icon('🎯') }} />
      <Tab.Screen name="Detective" component={DetectiveScreen} options={{ title: 'Dedektif', tabBarIcon: icon('🕵️') }} />
      <Tab.Screen name="Leaderboard" component={LeaderboardScreen} options={{ title: 'Liderlik', tabBarIcon: icon('🏆') }} />
      <Tab.Screen name="Profile" component={ProfileScreen} options={{ title: 'Profil', tabBarIcon: icon('👤') }} />
    </Tab.Navigator>
  );
}
