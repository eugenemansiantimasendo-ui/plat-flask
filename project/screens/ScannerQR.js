import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, FlatList, Alert, Vibration } from 'react-native';
import { RNCamera } from 'react-native-camera';
import Ionicons from 'react-native-vector-icons/Ionicons';

export default function ScannerQR() {
  const [clientData, setClientData] = useState(null);
  const [flash, setFlash] = useState(RNCamera.Constants.FlashMode.off);
  const [cameraType, setCameraType] = useState(RNCamera.Constants.Type.back);
  const [cameraReady, setCameraReady] = useState(false);

  const handleBarCodeRead = async ({ data }) => {
    if (!data) return;

    // Empêcher double scan
    if (clientData) return;

    try {
      const response = await fetch('https://tonserveur.com/reservation-public/scanner/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ qr_data: data }),
      });
      const result = await response.json();

      if (result.success) {
        Vibration.vibrate(200);
        setClientData(result);
      } else {
        Alert.alert("Erreur", result.message);
      }
    } catch (err) {
      Alert.alert("Erreur serveur", err.message);
    }
  };

  const servirClient = async () => {
    if (!clientData) return;

    try {
      const response = await fetch(
        `https://tonserveur.com/reservation-public/scanner/serve/${clientData.reservation_id}`,
        { method: 'POST' }
      );
      const result = await response.json();
      if (result.success) {
        Alert.alert("✅ Succès", result.message);
        setClientData(null);
      } else {
        Alert.alert("Erreur", result.message);
      }
    } catch (err) {
      Alert.alert("Erreur serveur", err.message);
    }
  };

  return (
    <View style={styles.container}>
      {!clientData ? (
        <>
          <RNCamera
            style={styles.preview}
            type={cameraType}
            flashMode={flash}
            androidCameraPermissionOptions={{
              title: 'Permission caméra',
              message: 'Nous avons besoin de votre permission pour accéder à la caméra',
              buttonPositive: 'OK',
              buttonNegative: 'Annuler',
            }}
            onBarCodeRead={handleBarCodeRead}
            onCameraReady={() => setCameraReady(true)}
            captureAudio={false}
          />

          {cameraReady && (
            <View style={styles.buttonsContainer}>
              <TouchableOpacity
                style={styles.flashButton}
                onPress={() =>
                  setFlash(
                    flash === RNCamera.Constants.FlashMode.torch
                      ? RNCamera.Constants.FlashMode.off
                      : RNCamera.Constants.FlashMode.torch
                  )
                }
              >
                <Ionicons
                  name={flash === RNCamera.Constants.FlashMode.torch ? "flash-off" : "flash"}
                  size={28}
                  color="white"
                />
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.switchButton}
                onPress={() =>
                  setCameraType(
                    cameraType === RNCamera.Constants.Type.back
                      ? RNCamera.Constants.Type.front
                      : RNCamera.Constants.Type.back
                  )
                }
              >
                <Ionicons name="camera-reverse" size={28} color="white" />
              </TouchableOpacity>
            </View>
          )}
        </>
      ) : (
        <View style={styles.result}>
          <Text style={styles.title}>Client : {clientData.client.nom}</Text>
          <Text>Email : {clientData.client.email}</Text>
          <Text>Téléphone : {clientData.client.tel}</Text>

          <Text style={styles.subtitle}>Plats réservés :</Text>
          <FlatList
            data={clientData.items}
            keyExtractor={(item, index) => index.toString()}
            renderItem={({ item }) => (
              <Text>- {item.plat} x{item.quantite} : ${item.prix * item.quantite}</Text>
            )}
          />

          <Text style={styles.total}>Total : ${clientData.total}</Text>

          <TouchableOpacity style={styles.serveButton} onPress={servirClient}>
            <Text style={{ color: 'white', fontWeight: 'bold' }}>✅ Servir le client</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center" },
  preview: { flex: 1 },
  buttonsContainer: { position: "absolute", bottom: 40, right: 30, flexDirection: "row" },
  flashButton: { marginRight: 15, backgroundColor: "#333", padding: 15, borderRadius: 50 },
  switchButton: { backgroundColor: "#555", padding: 15, borderRadius: 50 },
  result: { padding: 20, alignItems: "center" },
  title: { fontSize: 18, fontWeight: "bold", marginBottom: 10 },
  subtitle: { marginTop: 10, fontWeight: "600" },
  total: { marginTop: 10, fontSize: 16, fontWeight: "bold", color: "red" },
  serveButton: { marginTop: 15, padding: 12, backgroundColor: "green", borderRadius: 8 },
});
