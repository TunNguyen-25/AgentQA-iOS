import Foundation

struct Session { let token: String; let expiresAt: Date }

enum AuthError: Error {
    case invalidCredentials
    case termsNotAccepted
    case network(Error)
}

enum AuthService {
    /// POST /auth/login on the configured backend.
    static func login(username: String, password: String) async throws -> Session {
        var request = URLRequest(url: Backend.url("/auth/login"))
        request.httpMethod = "POST"
        request.httpBody = try JSONEncoder().encode(
            ["username": username, "password": password])
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw AuthError.invalidCredentials
        }
        return try JSONDecoder().decode(Session.self, from: data)
    }
}
