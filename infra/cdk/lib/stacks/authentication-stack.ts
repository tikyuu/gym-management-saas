import {
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
  Tags,
  aws_cognito as cognito,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface AuthenticationStackProps extends StackProps {
  applicationName: string;
  customerOAuthCallbackUrls: string[];
  customerOAuthLogoutUrls: string[];
  customerUserPoolDomainPrefix: string;
  environmentName: string;
  removalPolicy: RemovalPolicy;
  userPoolDeletionProtection: boolean;
}

export class AuthenticationStack extends Stack {
  public readonly customerAppClient: cognito.IUserPoolClient;
  public readonly customerUserPool: cognito.IUserPool;

  constructor(scope: Construct, id: string, props: AuthenticationStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "authentication");

    this.customerUserPool = new cognito.UserPool(this, "CustomerUserPool", {
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      autoVerify: {
        email: true,
      },
      deletionProtection: props.userPoolDeletionProtection,
      featurePlan: cognito.FeaturePlan.ESSENTIALS,
      mfa: cognito.Mfa.OPTIONAL,
      mfaSecondFactor: {
        otp: true,
        sms: false,
      },
      passwordPolicy: {
        minLength: 8,
        requireDigits: true,
        requireLowercase: true,
        requireSymbols: true,
        requireUppercase: true,
        tempPasswordValidity: Duration.days(7),
      },
      removalPolicy: props.removalPolicy,
      selfSignUpEnabled: true,
      signInAliases: {
        email: true,
      },
      signInCaseSensitive: false,
      userPoolName: `${resourceNamePrefix}-customer-user-pool`,
    });

    const customerUserPoolDomain = this.customerUserPool.addDomain(
      "CustomerUserPoolDomain",
      {
        cognitoDomain: {
          domainPrefix: props.customerUserPoolDomainPrefix,
        },
        managedLoginVersion: cognito.ManagedLoginVersion.NEWER_MANAGED_LOGIN,
      },
    );

    this.customerAppClient = new cognito.UserPoolClient(
      this,
      "CustomerAppClient",
      {
        accessTokenValidity: Duration.minutes(60),
        enableTokenRevocation: true,
        generateSecret: false,
        idTokenValidity: Duration.minutes(60),
        oAuth: {
          callbackUrls: props.customerOAuthCallbackUrls,
          flows: {
            authorizationCodeGrant: true,
            implicitCodeGrant: false,
          },
          logoutUrls: props.customerOAuthLogoutUrls,
          scopes: [cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL],
        },
        preventUserExistenceErrors: true,
        refreshTokenRotationGracePeriod: Duration.seconds(10),
        refreshTokenValidity: Duration.days(30),
        userPool: this.customerUserPool,
        userPoolClientName: `${resourceNamePrefix}-customer-app-client`,
      },
    );

    const customerManagedLoginBranding = new cognito.CfnManagedLoginBranding(
      this,
      "CustomerManagedLoginBranding",
      {
        clientId: this.customerAppClient.userPoolClientId,
        useCognitoProvidedValues: true,
        userPoolId: this.customerUserPool.userPoolId,
      },
    );

    customerManagedLoginBranding.node.addDependency(customerUserPoolDomain);
  }
}
