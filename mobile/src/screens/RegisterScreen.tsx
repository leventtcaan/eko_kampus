import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import apiClient from '../api/client';

export default function RegisterScreen({ navigation }: any) {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    if (!firstName.trim() || !lastName.trim() || !email.trim() || !password) {
      Alert.alert('Hata', 'Tüm alanları doldurun.');
      return;
    }

    setLoading(true);
    try {
      await apiClient.post('auth/register/', {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim().toLowerCase(),
        username: email.trim().toLowerCase().split('@')[0],
        password,
      });
      Alert.alert(
        'Kayıt Başarılı',
        'Hesabın oluşturuldu! Şimdi giriş yapabilirsin.',
        [{ text: 'Giriş Yap', onPress: () => navigation.navigate('Login') }],
      );
    } catch (error: any) {
      const data = error?.response?.data;
      const message = data
        ? Object.values(data).flat().join('\n')
        : 'Kayıt başarısız.';
      Alert.alert('Hata', message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.inner} keyboardShouldPersistTaps="handled">
        {/* Logo */}
        <View style={styles.logoBox}>
          <Text style={styles.logoEmoji}>🌿</Text>
          <Text style={styles.appName}>Eko-Kampüs</Text>
          <Text style={styles.university}>Akdeniz Üniversitesi</Text>
        </View>

        {/* Form */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Kayıt Ol</Text>

          <View style={styles.row}>
            <View style={styles.half}>
              <Text style={styles.label}>Ad</Text>
              <TextInput
                style={styles.input}
                placeholder="Levent"
                placeholderTextColor="#bbb"
                value={firstName}
                onChangeText={setFirstName}
              />
            </View>
            <View style={styles.half}>
              <Text style={styles.label}>Soyad</Text>
              <TextInput
                style={styles.input}
                placeholder="Can"
                placeholderTextColor="#bbb"
                value={lastName}
                onChangeText={setLastName}
              />
            </View>
          </View>

          <Text style={styles.label}>E-posta</Text>
          <TextInput
            style={styles.input}
            placeholder="@ogr.akdeniz.edu.tr ile biten mail"
            placeholderTextColor="#bbb"
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
          />

          <Text style={styles.label}>Şifre</Text>
          <TextInput
            style={styles.input}
            placeholder="••••••••"
            placeholderTextColor="#bbb"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />

          <Text style={styles.hint}>
            * Yalnızca @ogr.akdeniz.edu.tr uzantılı e-postalar kabul edilir.
          </Text>

          <TouchableOpacity
            style={[styles.btn, loading && styles.btnDisabled]}
            onPress={handleRegister}
            disabled={loading}
          >
            {loading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.btnText}>Kayıt Ol</Text>
            }
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.loginLink}
            onPress={() => navigation.navigate('Login')}
          >
            <Text style={styles.loginLinkText}>
              Zaten hesabın var mı? <Text style={styles.loginLinkBold}>Giriş Yap</Text>
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f0f5f0',
  },
  inner: {
    padding: 24,
    justifyContent: 'center',
    flexGrow: 1,
  },
  logoBox: {
    alignItems: 'center',
    marginBottom: 28,
  },
  logoEmoji: {
    fontSize: 48,
    marginBottom: 6,
  },
  appName: {
    fontSize: 24,
    fontWeight: '800',
    color: '#1a1a1a',
  },
  university: {
    fontSize: 13,
    fontWeight: '600',
    color: '#4CAF50',
    marginTop: 2,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 5,
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1a1a1a',
    marginBottom: 20,
  },
  row: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 0,
  },
  half: {
    flex: 1,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    color: '#555',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#f7f8f7',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#e8e8e8',
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 14,
    color: '#1a1a1a',
    marginBottom: 16,
  },
  hint: {
    fontSize: 11,
    color: '#aaa',
    marginBottom: 16,
    marginTop: -8,
  },
  btn: {
    backgroundColor: '#4CAF50',
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: 'center',
    shadowColor: '#4CAF50',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    elevation: 4,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  btnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  loginLink: {
    marginTop: 16,
    alignItems: 'center',
  },
  loginLinkText: {
    fontSize: 14,
    color: '#888',
  },
  loginLinkBold: {
    color: '#4CAF50',
    fontWeight: '700',
  },
});
