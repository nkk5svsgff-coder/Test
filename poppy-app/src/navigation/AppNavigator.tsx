import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors, Typography, Shadows } from '../theme';
import { useApp } from '../context/AppContext';

// Screens
import { WelcomeScreen } from '../screens/auth/WelcomeScreen';
import { SignUpScreen } from '../screens/auth/SignUpScreen';
import { LoginScreen } from '../screens/auth/LoginScreen';
import { DiscoverScreen } from '../screens/discover/DiscoverScreen';
import { MatchesScreen } from '../screens/matches/MatchesScreen';
import { ChatScreen } from '../screens/chat/ChatScreen';
import { ProfileScreen } from '../screens/profile/ProfileScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

const AuthStack = () => (
  <Stack.Navigator screenOptions={{ headerShown: false }}>
    <Stack.Screen name="Welcome" component={WelcomeScreen} />
    <Stack.Screen name="SignUp" component={SignUpScreen} />
    <Stack.Screen name="Login" component={LoginScreen} />
  </Stack.Navigator>
);

const MainTabs = () => {
  const { matches } = useApp();
  const totalUnread = matches.reduce((sum, m) => sum + m.unreadCount, 0);

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarStyle: {
          backgroundColor: Colors.white,
          borderTopWidth: 0,
          height: 85,
          paddingBottom: 20,
          paddingTop: 8,
          ...Shadows.medium,
        },
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.gray,
        tabBarLabelStyle: {
          ...Typography.labelSmall,
          fontSize: 11,
        },
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: keyof typeof Ionicons.glyphMap = 'heart';

          if (route.name === 'Discover') {
            iconName = focused ? 'mic' : 'mic-outline';
          } else if (route.name === 'Matches') {
            iconName = focused ? 'chatbubble-ellipses' : 'chatbubble-ellipses-outline';
          } else if (route.name === 'Profile') {
            iconName = focused ? 'person' : 'person-outline';
          }

          if (focused) {
            return (
              <View style={styles.activeTab}>
                <LinearGradient
                  colors={Colors.gradientPrimary as unknown as [string, string]}
                  style={styles.activeTabGradient}
                >
                  <Ionicons name={iconName} size={22} color={Colors.white} />
                </LinearGradient>
              </View>
            );
          }

          return <Ionicons name={iconName} size={24} color={color} />;
        },
      })}
    >
      <Tab.Screen
        name="Discover"
        component={DiscoverScreen}
        options={{ tabBarLabel: 'Discover' }}
      />
      <Tab.Screen
        name="Matches"
        component={MatchesScreen}
        options={{
          tabBarLabel: 'Messages',
          tabBarBadge: totalUnread > 0 ? totalUnread : undefined,
          tabBarBadgeStyle: {
            backgroundColor: Colors.primary,
            color: Colors.white,
            fontSize: 10,
            fontWeight: '700',
            minWidth: 18,
            height: 18,
            lineHeight: 18,
          },
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ tabBarLabel: 'Profile' }}
      />
    </Tab.Navigator>
  );
};

const MainStack = () => (
  <Stack.Navigator screenOptions={{ headerShown: false }}>
    <Stack.Screen name="MainTabs" component={MainTabs} />
    <Stack.Screen
      name="Chat"
      component={ChatScreen}
      options={{
        animation: 'slide_from_right',
      }}
    />
  </Stack.Navigator>
);

export const AppNavigator: React.FC = () => {
  const { isAuthenticated } = useApp();

  return (
    <NavigationContainer>
      {isAuthenticated ? <MainStack /> : <AuthStack />}
    </NavigationContainer>
  );
};

const styles = StyleSheet.create({
  activeTab: {
    ...Shadows.glow,
  },
  activeTabGradient: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: -8,
  },
});
